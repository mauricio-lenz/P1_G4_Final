using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Build movil inicial (Android) del viewer.
/// Menu: MCOC / Build Android (APK)
/// Consola: Unity.exe -batchmode -quit -projectPath edificio_G4 -executeMethod BuildAndroid.Build
/// Salida: edificio_G4/Builds/Android/P1G4_Viewer.apk
/// </summary>
public static class BuildAndroid
{
    private const string Scene = "Assets/Scenes/StructureViewerScene.unity";
    private const string OutputDir = "Builds/Android";
    private const string ApkName = "P1G4_Viewer.apk";

    [MenuItem("MCOC/Build Android (APK)")]
    public static void BuildFromMenu()
    {
        Build();
    }

    public static void Configure()
    {
        PlayerSettings.companyName = "UANDES MCOC Grupo 4";
        PlayerSettings.productName = "P1_G4 Viewer";
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android, "cl.uandes.mcoc.p1g4");
        PlayerSettings.bundleVersion = "0.5.0";
        PlayerSettings.Android.bundleVersionCode = 5;

        // Telefono de referencia: Samsung Galaxy A54 (Android 13, ARM64, Vulkan 1.1 / GLES 3.2)
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel29;
        PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
        PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.Vulkan, GraphicsDeviceType.OpenGLES3 });

        IncludeRuntimeShaders();

        // El panel del viewer esta pensado para pantalla horizontal
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
        PlayerSettings.allowedAutorotateToPortrait = false;
        PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
        PlayerSettings.allowedAutorotateToLandscapeLeft = true;
        PlayerSettings.allowedAutorotateToLandscapeRight = true;
    }

    /// Los materiales del viewer se crean en tiempo de ejecucion con Shader.Find:
    /// esos shaders deben ir en "Always Included Shaders" o Unity los elimina del build.
    private static void IncludeRuntimeShaders()
    {
        string[] names = { "Custom/AlwaysOnTopLine", "Standard", "Unlit/Color", "Sprites/Default" };
        var graphics = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>("ProjectSettings/GraphicsSettings.asset");
        var so = new SerializedObject(graphics);
        SerializedProperty list = so.FindProperty("m_AlwaysIncludedShaders");
        foreach (string name in names)
        {
            Shader shader = Shader.Find(name);
            if (shader == null)
            {
                Debug.LogWarning("[BuildAndroid] No se encontro el shader " + name);
                continue;
            }
            bool present = false;
            for (int i = 0; i < list.arraySize; i++)
            {
                if (list.GetArrayElementAtIndex(i).objectReferenceValue == shader) { present = true; break; }
            }
            if (!present)
            {
                list.InsertArrayElementAtIndex(list.arraySize);
                list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = shader;
                Debug.Log("[BuildAndroid] Shader incluido en el build: " + name);
            }
        }
        so.ApplyModifiedProperties();
        AssetDatabase.SaveAssets();
    }

    [MenuItem("MCOC/Build Android de diagnostico (APK)")]
    public static void BuildDevelopmentFromMenu()
    {
        BuildDevelopment();
    }

    /// Build de desarrollo: muestra en pantalla la consola de diagnostico (DebugOverlay).
    public static void BuildDevelopment()
    {
        Build(true);
    }

    public static void Build()
    {
        Build(false);
    }

    // ------------------------------------------------------------------
    // Semana 6: APK de AR (ARScene, ARCore). Se instala aparte del viewer.
    // ------------------------------------------------------------------
    [MenuItem("MCOC/AR/Build Android AR (APK)")]
    public static void BuildARFromMenu()
    {
        BuildAR();
    }

    public static void BuildAR()
    {
        Configure();
        PlayerSettings.productName = "P1_G4 AR";
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android, "cl.uandes.mcoc.p1g4.ar");
        // ARCore: OpenGLES3 es la API grafica mas compatible
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
        // El renderizado multihilo provoca GL_INVALID_ENUM con el fondo de camara de ARCore
        PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android, false);
        // Con GameActivity ARCore recibia ~7 muestras/s de IMU (necesita ~200): se usa la Activity clasica
        PlayerSettings.Android.applicationEntry = AndroidApplicationEntry.Activity;
        ARSetup.ConfigureXR(true);
        ARSetup.CreateARScene();   // la escena se genera por codigo: siempre al dia

        Directory.CreateDirectory(OutputDir);
        var options = new BuildPlayerOptions
        {
            scenes = new[] { ARSetup.ScenePath },
            locationPathName = Path.Combine(OutputDir, "P1G4_AR.apk"),
            target = BuildTarget.Android,
            targetGroup = BuildTargetGroup.Android,
            options = BuildOptions.Development   // consola de errores en pantalla durante las pruebas
        };
        EditorUserBuildSettings.buildAppBundle = false;
        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary summary = report.summary;
        Debug.Log($"[BuildAndroid] AR {summary.result} | {summary.outputPath} | {summary.totalSize / (1024f * 1024f):0.0} MB | " +
                  $"{summary.totalErrors} errores, {summary.totalWarnings} avisos, {summary.totalTime}");
        ARSetup.ConfigureXR(false);   // deja el proyecto listo para el viewer normal
        if (Application.isBatchMode && summary.result != BuildResult.Succeeded)
        {
            EditorApplication.Exit(1);
        }
    }

    private static void Build(bool development)
    {
        Configure();
        ARSetup.ConfigureXR(false);   // el viewer no inicia la sesion AR
        Directory.CreateDirectory(OutputDir);
        var options = new BuildPlayerOptions
        {
            scenes = new[] { Scene },
            locationPathName = Path.Combine(OutputDir, development ? "P1G4_Viewer_diagnostico.apk" : ApkName),
            target = BuildTarget.Android,
            targetGroup = BuildTargetGroup.Android,
            options = development ? BuildOptions.Development : BuildOptions.None
        };
        EditorUserBuildSettings.buildAppBundle = false;   // APK instalable directamente

        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary summary = report.summary;
        Debug.Log($"[BuildAndroid] {summary.result} | {summary.outputPath} | {summary.totalSize / (1024f * 1024f):0.0} MB | " +
                  $"{summary.totalErrors} errores, {summary.totalWarnings} avisos, {summary.totalTime}");
        if (Application.isBatchMode && summary.result != BuildResult.Succeeded)
        {
            EditorApplication.Exit(1);
        }
    }
}
