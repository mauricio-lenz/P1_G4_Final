using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

/// <summary>
/// Parametros del analisis editados desde la interfaz y reanalisis completo con
/// OpenSees (scripts/exportar_resultados_unity.py) en segundo plano.
///
/// Flujo: se editan q_G, Q, coeficiente sismico, combinaciones y cambios de
/// seccion -> Reanalizar escribe combos.json y mods.json temporales y corre el
/// exportador con --out a un archivo temporal -> el viewer carga ese escenario.
/// "Guardar como modelo vigente" copia el escenario a Assets/Resources y escribe
/// data/combinaciones.json y data/parametros_analisis.json (el exportador los lee
/// por defecto, asi la exportacion desde VS Code da lo mismo).
/// </summary>
public class AnalysisSession
{
    public class Combo { public string name; public float G, Q, EX, EY; }
    public class Section { public int id; public string tag; public string before; public string sectionId; public float width, height; }

    public float qG = 6.227f;          // kN/m2
    public float qKgM2 = 500f;         // kg/m2
    public float seismicCoeff = 0.20f;
    public readonly List<Combo> combos = new List<Combo>();
    public readonly Dictionary<int, Section> sections = new Dictionary<int, Section>();

    public readonly PythonJob job = new PythonJob();
    public bool ScenarioLoaded { get; private set; }
    public string Message { get; set; } = "";
    public float LastDuration { get; private set; }
    private string scenarioPath;

    private const float KnPerKg = 0.00980665f;
    private static readonly Encoding NoBom = new UTF8Encoding(false);   // Python json no acepta BOM
    private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    /// Toma los valores del modelo cargado (parametros, combinaciones y secciones ya aplicadas).
    public void LoadFrom(StructureData d)
    {
        if (d == null) return;
        qG = d.q_G > 0f ? d.q_G : 6.227f;
        qKgM2 = d.Q_kN_m2 > 0f ? d.Q_kN_m2 / KnPerKg : 500f;
        seismicCoeff = d.seismic_coefficient > 0f ? d.seismic_coefficient : 0.20f;
        combos.Clear();
        if (d.p1l4?.combinations != null)
        {
            foreach (ComboInfo c in d.p1l4.combinations)
                combos.Add(new Combo { name = c.name, G = c.G, Q = c.Q, EX = c.EX, EY = c.EY });
        }
        sections.Clear();
        if (d.resumenAnalisis?.secciones != null)
        {
            foreach (SectionChange s in d.resumenAnalisis.secciones)
            {
                ElementData e = System.Array.Find(d.elements, x => x.id == s.id);
                if (e != null) sections[s.id] = new Section { id = s.id, tag = s.tag, before = s.antes, sectionId = s.despues, width = e.width_m, height = e.height_m };
            }
        }
    }

    public void SetSection(ElementData e, string sectionId, float width, float height, string originalSection)
    {
        sections[e.id] = new Section { id = e.id, tag = e.elementTag, before = originalSection, sectionId = sectionId, width = width, height = height };
    }

    // ------------------------------------------------------------------
    public bool StartReanalysis()
    {
        if (job.Running) return false;
        string dir = Application.temporaryCachePath;
        string combosPath = Path.Combine(dir, "combos_unity.json");
        string modsPath = Path.Combine(dir, "mods_unity.json");
        File.WriteAllText(combosPath, CombosJson("Combinaciones editadas en Unity (escenario de reanalisis)."), NoBom);
        File.WriteAllText(modsPath, "{\"sections\": " + SectionsJson() + "}", NoBom);
        string args = string.Format(Inv, "--q-kg-m2 {0} --sc {1} --qG {2} --combos \"{3}\" --mods \"{4}\"",
            qKgM2, seismicCoeff, qG, combosPath, modsPath);
        if (!job.Start("exportar_resultados_unity.py", args, "escenario_unity.json"))
        {
            Message = job.Error;
            return false;
        }
        Message = "Analizando con OpenSees...";
        return true;
    }

    /// Llamar en Update; true cuando el reanalisis termino y se cargo en el viewer.
    public bool Poll(StructureViewer viewer)
    {
        if (!job.Poll(300f)) return false;
        LastDuration = job.Elapsed;
        if (job.Error != null)
        {
            Message = job.Error;
            return false;
        }
        scenarioPath = job.OutputPath;
        ScenarioLoaded = true;   // antes de recargar: la interfaz se reconstruye en ReloadFromJson
        viewer.ReloadFromJson(File.ReadAllText(scenarioPath), "escenario de reanálisis (sin guardar)");
        Message = $"Reanálisis listo en {LastDuration:0} s. Escenario cargado (sin guardar).";
        return true;
    }

    /// Copia el escenario al proyecto y guarda combinaciones y parametros.
    public bool SaveAsCurrent(StructureViewer viewer)
    {
        string root = PythonJob.ProjectRoot;
        string target = StructureViewer.ProjectJsonPath;
        if (!ScenarioLoaded || scenarioPath == null || !File.Exists(scenarioPath) || root == null || target == null)
        {
            Message = "No hay un escenario para guardar.";
            return false;
        }
        File.Copy(scenarioPath, target, true);
        File.WriteAllText(Path.Combine(root, "data", "combinaciones.json"),
            CombosJson("Factores editados desde Unity (pestaña ANÁLISIS)."), NoBom);
        File.WriteAllText(Path.Combine(root, "data", "parametros_analisis.json"), ParamsJson(), NoBom);
#if UNITY_EDITOR
        UnityEditor.AssetDatabase.ImportAsset("Assets/Resources/estructura_p1l4_unity.json");
#endif
        ScenarioLoaded = false;
        viewer.Status = "Modelo vigente actualizado.";
        Message = "Guardado: Assets/Resources/estructura_p1l4_unity.json, data/combinaciones.json y data/parametros_analisis.json.";
        return true;
    }

    public void DiscardScenario(StructureViewer viewer)
    {
        ScenarioLoaded = false;
        viewer.ReloadOriginal();
        LoadFrom(viewer.Data);
        Message = "Se volvió al modelo vigente.";
    }

    // ------------------------------------------------------------------
    private string CombosJson(string origen)
    {
        var sb = new StringBuilder();
        sb.Append("{\n  \"descripcion\": \"Combinaciones de carga del proyecto. Editar aqui (VS Code) o desde Unity (pestaña ANÁLISIS) y re-exportar: ")
          .Append("python -X utf8 Proyecto1/scripts/exportar_resultados_unity.py. Cada combinacion es la suma lambda_G*G + lambda_Q*Q + lambda_EX*EX + lambda_EY*EY de los casos base.\",\n");
        sb.Append("  \"origen\": \"").Append(origen).Append("\",\n  \"combinaciones\": [\n");
        for (int i = 0; i < combos.Count; i++)
        {
            Combo c = combos[i];
            sb.Append(string.Format(Inv, "    {{\"name\": \"{0}\", \"G\": {1}, \"Q\": {2}, \"EX\": {3}, \"EY\": {4}}}", Escape(c.name), c.G, c.Q, c.EX, c.EY));
            sb.Append(i < combos.Count - 1 ? ",\n" : "\n");
        }
        sb.Append("  ]\n}\n");
        return sb.ToString();
    }

    private string SectionsJson()
    {
        var parts = new List<string>();
        foreach (Section s in sections.Values)
        {
            parts.Add(string.Format(Inv, "\"{0}\": {{\"width_m\": {1}, \"height_m\": {2}, \"sectionId\": \"{3}\"}}", s.id, s.width, s.height, Escape(s.sectionId)));
        }
        return "{" + string.Join(", ", parts) + "}";
    }

    private string ParamsJson()
    {
        return string.Format(Inv,
            "{{\n  \"descripcion\": \"Parametros del analisis (guardados desde Unity). Los lee exportar_resultados_unity.py y quitar_elemento.py; los argumentos de consola tienen prioridad.\",\n" +
            "  \"Q_kg_m2\": {0},\n  \"coeficienteSismico\": {1},\n  \"q_G_kN_m2\": {2},\n  \"sections\": {3}\n}}\n",
            qKgM2, seismicCoeff, qG, SectionsJson());
    }

    private static string Escape(string s) => (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"");
}
