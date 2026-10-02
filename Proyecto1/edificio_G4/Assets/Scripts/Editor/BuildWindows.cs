using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

/// <summary>
/// Build de escritorio (Windows) del viewer.
/// Menu: MCOC / Build Windows (viewer)
/// Consola: Unity.exe -batchmode -quit -projectPath edificio_G4 -executeMethod BuildWindows.Build
/// Salida: edificio_G4/Builds/Windows/P1G4_Viewer.exe  (P1G4_Viewer.exe -autoshot <carpeta> para capturas)
/// </summary>
public static class BuildWindows
{
    [MenuItem("MCOC/Build Windows (viewer)")]
    public static void BuildFromMenu()
    {
        Build();
    }

    /// Windows: solo Direct3D 11 (el editor tambien lo usa al reabrir el proyecto).
    [MenuItem("MCOC/Usar Direct3D 11 en Windows")]
    public static void UseD3D11()
    {
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { UnityEngine.Rendering.GraphicsDeviceType.Direct3D11 });
        AssetDatabase.SaveAssets();
        Debug.Log("[BuildWindows] Graphics API Windows = Direct3D 11");
    }

    public static void Build()
    {
        ARSetup.ConfigureXR(false);
        PlayerSettings.productName = "P1_G4 Viewer";
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.defaultScreenWidth = 1600;
        PlayerSettings.defaultScreenHeight = 900;
        PlayerSettings.resizableWindow = true;
        PlayerSettings.runInBackground = true;
        // D3D12 se cae en este notebook (Intel + RTX 3060) en el hilo de render: se usa D3D11
        UseD3D11();
        Directory.CreateDirectory("Builds/Windows");
        var options = new BuildPlayerOptions
        {
            scenes = new[] { "Assets/Scenes/StructureViewerScene.unity" },
            locationPathName = "Builds/Windows/P1G4_Viewer.exe",
            target = BuildTarget.StandaloneWindows64,
            targetGroup = BuildTargetGroup.Standalone,
            options = BuildOptions.None
        };
        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary s = report.summary;
        Debug.Log($"[BuildWindows] {s.result} | {s.outputPath} | {s.totalSize / (1024f * 1024f):0.0} MB | {s.totalErrors} errores");
        if (Application.isBatchMode && s.result != BuildResult.Succeeded) EditorApplication.Exit(1);
    }
}
