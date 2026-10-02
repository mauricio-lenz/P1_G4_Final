using System.Collections;
using System.IO;
using UnityEngine;

/// <summary>
/// Capturas automaticas de la interfaz en un build de escritorio:
///   P1G4_Viewer.exe -autoshot C:\carpeta
/// Recorre las pestanas y algunos resultados, guarda PNG y cierra la app.
/// Sirve para revisar la interfaz sin operar el viewer a mano.
/// </summary>
public class AutoShot : MonoBehaviour
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    private static void Boot()
    {
        string dir = Arg("-autoshot");
        if (string.IsNullOrEmpty(dir)) return;
        var go = new GameObject("AutoShot");
        go.AddComponent<AutoShot>().outDir = dir;
        DontDestroyOnLoad(go);
    }

    private string outDir;

    private IEnumerator Start()
    {
        Directory.CreateDirectory(outDir);
        yield return new WaitForSeconds(3f);
        var viewer = FindAnyObjectByType<StructureViewer>();
        if (viewer == null) { Application.Quit(); yield break; }

        yield return Shot("01_vista");
        viewer.SetCase("C1");
        viewer.Search("E1_72");
        viewer.SetResult("Momento");
        ViewerUI.ShowTab(ViewerUI.TabResultados);
        yield return new WaitForSeconds(1.5f);
        yield return Shot("02_resultados_momento");
        ViewerUI.ShowTab(ViewerUI.TabCargas);
        yield return Shot("03_cargas");
        ViewerUI.ShowTab(ViewerUI.TabModificar);
        yield return Shot("04_modificar");
        ViewerUI.ShowTab(ViewerUI.TabAnalisis);
        yield return Shot("05_analisis");
        DiagramController.AnimateDeformed = false;
        viewer.SetResult("Deformada");
        ViewerUI.ShowTab(ViewerUI.TabResultados);
        yield return new WaitForSeconds(1f);
        yield return Shot("06_deformada");

        if (System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-reanalyze") >= 0)
        {
            // reanalisis de prueba: q_G 7 kN/m2 y E1_72 como V40/80
            viewer.SetResult("Momento");
            viewer.Search("E1_72");
            yield return new WaitForSeconds(0.5f);
            var picker = FindAnyObjectByType<ElementPicker>();
            if (picker != null && picker.Selected != null)
                ViewerUI.Session.SetSection(picker.Selected.data, "V40/80", 0.4f, 0.8f, picker.Selected.data.sectionId);
            ViewerUI.Session.qG = 7f;
            ViewerUI.ShowTab(ViewerUI.TabModificar);
            yield return Shot("07_modificar_seccion");
            ViewerUI.ShowTab(ViewerUI.TabAnalisis);
            ViewerUI.Session.StartReanalysis();
            yield return new WaitForSeconds(2f);
            yield return Shot("08_reanalizando");
            float t0 = Time.unscaledTime;
            while (ViewerUI.Session.job.Running && Time.unscaledTime - t0 < 240f) yield return null;
            yield return new WaitForSeconds(2f);
            yield return Shot("09_escenario_cargado");
        }
        Application.Quit();
    }

    private IEnumerator Shot(string name)
    {
        yield return new WaitForSeconds(0.6f);
        yield return new WaitForEndOfFrame();   // todo dibujado: escena, UI Toolkit e IMGUI
        var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
        tex.Apply();
        File.WriteAllBytes(Path.Combine(outDir, name + ".png"), tex.EncodeToPNG());
        Destroy(tex);
        yield return new WaitForSeconds(0.2f);
    }

    private static string Arg(string name)
    {
        string[] args = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++) if (args[i] == name) return args[i + 1];
        return null;
    }
}
