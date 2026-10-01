using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// Capturas del viewer sin abrir el editor (revision visual de diagramas).
/// Consola: Unity.exe -batchmode -quit -projectPath edificio_G4 -executeMethod ViewerCapture.Capture
///          -captureOut <carpeta> [-captureCombo C1]
/// Genera iso_<modo>.png y detalle_<modo>.png para Momento, Corte, Axial y Deformada.
/// </summary>
public static class ViewerCapture
{
    private const string Scene = "Assets/Scenes/StructureViewerScene.unity";

    [MenuItem("MCOC/Capturas de diagramas (PNG)")]
    public static void CaptureFromMenu()
    {
        Capture();
    }

    public static void Capture()
    {
        string outDir = Arg("-captureOut") ?? Path.GetFullPath("Builds/Capturas");
        string combo = Arg("-captureCombo") ?? "C1";
        Directory.CreateDirectory(outDir);

        EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
        var viewer = Object.FindAnyObjectByType<StructureViewer>();
        var diagrams = Object.FindAnyObjectByType<DiagramController>();
        if (viewer == null || diagrams == null || UnityData.Structure == null)
        {
            Debug.LogError("[ViewerCapture] La escena no construyo el modelo (StructureViewer/DiagramController).");
            return;
        }
        UnityData.ActiveCombo = combo;

        Camera cam = Camera.main;
        if (cam == null) cam = new GameObject("CaptureCamera").AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.035f, 0.05f, 0.095f);
        cam.fieldOfView = 40f;
        cam.farClipPlane = 1000f;

        // vistas: edificio completo (iso) y detalle de la viga E1_72 (modelo x 0-7.51, y -11.37, z 7.92)
        var views = new (string name, Vector3 pos, Vector3 target)[]
        {
            ("iso", new Vector3(75f, 55f, -85f), new Vector3(-2f, 6f, -4f)),
            ("detalle", new Vector3(8f, 11f, -32f), new Vector3(4f, 7.5f, -9f)),
        };
        foreach (string mode in new[] { "Momento", "Corte", "Axial", "Deformada" })
        {
            diagrams.SetResultMode(mode);
            foreach (var v in views)
            {
                cam.transform.position = v.pos;
                cam.transform.LookAt(v.target);
                string file = Path.Combine(outDir, $"{v.name}_{mode}.png");
                Render(cam, file, 1600, 900);
            }
        }
        diagrams.SetResultMode("None");
        Debug.Log("[ViewerCapture] Capturas en " + outDir);
    }

    private static void Render(Camera cam, string file, int w, int h)
    {
        var rt = new RenderTexture(w, h, 24) { antiAliasing = 4 };
        cam.targetTexture = rt;
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        File.WriteAllBytes(file, tex.EncodeToPNG());
        cam.targetTexture = null;
        RenderTexture.active = null;
        Object.DestroyImmediate(rt);
        Object.DestroyImmediate(tex);
    }

    private static string Arg(string name)
    {
        string[] args = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++) if (args[i] == name) return args[i + 1];
        return null;
    }
}
