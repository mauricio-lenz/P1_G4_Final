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
    /// Cambio de armadura (null = sin cambio en ese campo). Vigas: inferior, superior, supleApoyo,
    /// estribosApoyo, estribosTramo. Columnas: barras, estribos.
    public class Arm
    {
        public string inferior, superior, supleApoyo, estribosApoyo, estribosTramo, barras, estribos;
        public string Describe()
        {
            var p = new List<string>();
            if (inferior != null) p.Add("inf " + inferior);
            if (superior != null) p.Add("sup " + superior);
            if (supleApoyo != null) p.Add("suple " + supleApoyo);
            if (estribosApoyo != null) p.Add("E apoyo " + estribosApoyo);
            if (estribosTramo != null) p.Add("E tramo " + estribosTramo);
            if (barras != null) p.Add(barras);
            if (estribos != null) p.Add("E " + estribos);
            return string.Join(" · ", p);
        }
    }
    /// Cambios de armadura por elemento (elementTag) y por seccion (sectionId).
    public readonly Dictionary<string, Arm> armElem = new Dictionary<string, Arm>();
    public readonly Dictionary<string, Arm> armSec = new Dictionary<string, Arm>();
    public bool HasArmChanges => armElem.Count > 0 || armSec.Count > 0;

    public float qG = 6.227f;          // kN/m2
    public float qKgM2 = 500f;         // kg/m2
    public float qCubiertaKgM2 = 200f; // kg/m2, nivel superior de cada edificio
    public float seismicCoeff = 0.20f;   // C del metodo fijo
    /// Sismo NCh433 estatico (DS61): zona, suelo, R, I y fraccion de Q en el peso sismico.
    public bool sismoNCh = true;
    public int zona = 3;
    public string suelo = "C";
    public float R = 7f, I = 1f, fraccionQ = 0.25f;
    /// Factores de inercia por tipo (rigidez fisurada; 1 = seccion bruta). ACI 318: 0,35 / 0,70 / 0,35.
    public float kViga = 0.35f, kColumna = 0.70f, kMuro = 0.35f;
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
        qCubiertaKgM2 = d.Q_cubierta_kN_m2 > 0f ? d.Q_cubierta_kN_m2 / KnPerKg : qKgM2;
        seismicCoeff = d.seismic_coefficient > 0f ? d.seismic_coefficient : 0.20f;
        SismoSummary sis = d.resumenAnalisis?.sismo;
        if (sis != null && !string.IsNullOrEmpty(sis.metodo))
        {
            sismoNCh = sis.metodo == "NCh433";
            if (sis.C_fijo > 0f) seismicCoeff = sis.C_fijo;
            if (sismoNCh)
            {
                zona = sis.zona;
                suelo = sis.suelo;
                R = sis.R;
                I = sis.I;
                fraccionQ = sis.fraccionQ;
            }
        }
        if (d.resumenAnalisis != null && d.resumenAnalisis.rigidezViga > 0f)
        {
            kViga = d.resumenAnalisis.rigidezViga;
            kColumna = d.resumenAnalisis.rigidezColumna;
            kMuro = d.resumenAnalisis.rigidezMuro;
        }
        combos.Clear();
        if (d.p1l4?.combinations != null)
        {
            foreach (ComboInfo c in d.p1l4.combinations)
                combos.Add(new Combo { name = c.name, G = c.G, Q = c.Q, EX = c.EX, EY = c.EY });
        }
        armElem.Clear();
        armSec.Clear();
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
    /// Revision rapida en Unity antes de lanzar Python (el exportador vuelve a validar todo).
    public string ValidateInputs()
    {
        var problems = new List<string>();
        if (qKgM2 < 0f || qKgM2 > 5000f) problems.Add($"Q = {qKgM2:0} kg/m² fuera de 0-5000");
        if (qCubiertaKgM2 < 0f || qCubiertaKgM2 > 5000f) problems.Add($"Q cubierta = {qCubiertaKgM2:0} kg/m² fuera de 0-5000");
        if (qG <= 0f || qG > 50f) problems.Add($"q_G = {qG:0.###} kN/m² fuera de 0-50");
        foreach (var (name, k) in new[] { ("vigas", kViga), ("columnas", kColumna), ("muros", kMuro) })
            if (k < 0.05f || k > 1f) problems.Add($"rigidez de {name} = {k:0.##} fuera de 0,05-1");
        if (sismoNCh)
        {
            if (zona < 1 || zona > 3) problems.Add($"zona sísmica {zona} (1 a 3)");
            if (R < 1f || R > 11f) problems.Add($"R = {R:0.#} fuera de 1-11");
            if (I < 0.5f || I > 1.5f) problems.Add($"I = {I:0.##} fuera de 0,5-1,5");
        }
        else if (seismicCoeff < 0f || seismicCoeff > 1.5f) problems.Add($"C = {seismicCoeff:0.###} fuera de 0-1,5");
        var names = new HashSet<string>();
        foreach (Combo c in combos)
        {
            if (string.IsNullOrWhiteSpace(c.name) || !names.Add(c.name)) problems.Add($"combinación sin nombre o repetida ({c.name})");
            foreach (float l in new[] { c.G, c.Q, c.EX, c.EY })
                if (float.IsNaN(l) || Mathf.Abs(l) > 5f) { problems.Add($"{c.name}: |λ| > 5"); break; }
        }
        return problems.Count == 0 ? null : "Revisar: " + string.Join("; ", problems);
    }

    public bool StartReanalysis()
    {
        if (job.Running) return false;
        string invalid = ValidateInputs();
        if (invalid != null)
        {
            Message = invalid;
            return false;
        }
        string dir = Application.temporaryCachePath;
        string combosPath = Path.Combine(dir, "combos_unity.json");
        string modsPath = Path.Combine(dir, "mods_unity.json");
        File.WriteAllText(combosPath, CombosJson("Combinaciones editadas en Unity (escenario de reanalisis)."), NoBom);
        File.WriteAllText(modsPath, "{\"sections\": " + SectionsJson() + "}", NoBom);
        string args = string.Format(Inv, "--q-kg-m2 {0} --q-cubierta-kg-m2 {8} {1} --qG {2} --combos \"{3}\" --mods \"{4}\" --fisurada {5},{6},{7}",
            qKgM2, SismoArgs(), qG, combosPath, modsPath, kViga, kColumna, kMuro, qCubiertaKgM2);
        if (HasArmChanges)
        {
            string armPath = Path.Combine(dir, "armaduras_unity.json");
            File.WriteAllText(armPath, ArmJson(), NoBom);
            args += " --armaduras \"" + armPath + "\"";
        }
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
        if (HasArmChanges && !MergeArmaduras(out string mergeError))
        {
            Message = "Modelo guardado, pero no se pudieron guardar las armaduras: " + mergeError;
        }
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

    /// Fusiona los cambios de armadura en data/armaduras.json (capacidad_ha.py --merge), esperando el proceso.
    private bool MergeArmaduras(out string error)
    {
        error = null;
#if UNITY_EDITOR || UNITY_STANDALONE
        string path = Path.Combine(Application.temporaryCachePath, "armaduras_guardar.json");
        File.WriteAllText(path, ArmJson(), NoBom);
        foreach (string exe in new[] { "python", "py" })
        {
            try
            {
                var info = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = exe,
                    Arguments = $"-X utf8 \"{PythonJob.ScriptPath("capacidad_ha.py")}\" --merge \"{path}\"",
                    WorkingDirectory = PythonJob.ScriptsDir,
                    UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = true, RedirectStandardOutput = true
                };
                using (var p = System.Diagnostics.Process.Start(info))
                {
                    p.WaitForExit(30000);
                    if (p.ExitCode == 0) { armElem.Clear(); armSec.Clear(); return true; }
                    error = p.StandardError.ReadToEnd();
                    return false;
                }
            }
            catch (System.Exception e) { error = e.Message; }
        }
        return false;
#else
        error = "solo en PC";
        return false;
#endif
    }

    private static string ArmFields(Arm a)
    {
        var parts = new List<string>();
        void Add(string k, string v) { if (v != null) parts.Add($"\"{k}\": \"{Escape(v)}\""); }
        Add("inferior", a.inferior); Add("superior", a.superior); Add("supleApoyo", a.supleApoyo);
        Add("estribosApoyo", a.estribosApoyo); Add("estribosTramo", a.estribosTramo);
        Add("barras", a.barras); Add("estribos", a.estribos);
        return "{" + string.Join(", ", parts) + "}";
    }

    private string ArmJson()
    {
        var sec = new List<string>();
        foreach (var kv in armSec) sec.Add($"\"{Escape(kv.Key)}\": {ArmFields(kv.Value)}");
        var el = new List<string>();
        foreach (var kv in armElem) el.Add($"\"{Escape(kv.Key)}\": {ArmFields(kv.Value)}");
        return "{\n  \"secciones\": {" + string.Join(", ", sec) + "},\n  \"elementos\": {" + string.Join(", ", el) + "}\n}\n";
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
            "  \"Q_kg_m2\": {0},\n  \"Q_cubierta_kg_m2\": {8},\n  \"sismo\": {7},\n  \"coeficienteSismico\": {1},\n  \"q_G_kN_m2\": {2},\n" +
            "  \"rigidezFisurada\": {{\"viga\": {4}, \"columna\": {5}, \"muro\": {6}}},\n  \"sections\": {3}\n}}\n",
            qKgM2, seismicCoeff, qG, SectionsJson(), kViga, kColumna, kMuro, SismoJson(), qCubiertaKgM2);
    }

    /// Argumentos del sismo para exportar_resultados_unity.py.
    private string SismoArgs()
    {
        if (!sismoNCh) return string.Format(Inv, "--sc {0}", seismicCoeff);
        return string.Format(Inv, "--sismo nch433 --zona {0} --suelo {1} --R {2} --I {3} --fraccionQ {4}", zona, suelo, R, I, fraccionQ);
    }

    private string SismoJson()
    {
        return string.Format(Inv, "{{\"metodo\": \"{0}\", \"zona\": {1}, \"suelo\": \"{2}\", \"R\": {3}, \"I\": {4}, \"fraccionQ\": {5}}}",
            sismoNCh ? "NCh433" : "fijo", zona, Escape(suelo), R, I, fraccionQ);
    }

    private static string Escape(string s) => (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"");
}
