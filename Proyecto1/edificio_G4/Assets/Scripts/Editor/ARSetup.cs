using System.IO;
using Unity.XR.CoreUtils;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEditor.XR.ARSubsystems;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using UnityEngine.XR.Management;

/// <summary>
/// Semana 6 (AR): configuracion de XR (ARCore en Android) y creacion de la
/// escena Assets/Scenes/ARScene.unity (AR Session + XR Origin + camara AR).
/// Menu MCOC/AR o consola: -executeMethod ARSetup.SetupAll
/// </summary>
public static class ARSetup
{
    public const string ScenePath = "Assets/Scenes/ARScene.unity";
    private const string XRSettingsPath = "Assets/XR/XRGeneralSettingsPerBuildTarget.asset";
    private const string ARCoreLoader = "UnityEngine.XR.ARCore.ARCoreLoader";

    [MenuItem("MCOC/AR/Configurar XR y crear escena AR")]
    public static void SetupAll()
    {
        ConfigureXR(true);
        CreateARScene();
        AssetDatabase.SaveAssets();
        Debug.Log("[ARSetup] Listo: XR (ARCore) configurado y escena " + ScenePath + " creada.");
    }

    /// Activa el loader de ARCore para Android. initOnStart = false para el
    /// viewer normal (no inicia la sesion AR), true para el APK de AR.
    public static void ConfigureXR(bool initOnStart)
    {
        if (!EditorBuildSettings.TryGetConfigObject(XRGeneralSettings.k_SettingsKey, out XRGeneralSettingsPerBuildTarget perTarget) || perTarget == null)
        {
            Directory.CreateDirectory("Assets/XR");
            perTarget = ScriptableObject.CreateInstance<XRGeneralSettingsPerBuildTarget>();
            AssetDatabase.CreateAsset(perTarget, XRSettingsPath);
            EditorBuildSettings.AddConfigObject(XRGeneralSettings.k_SettingsKey, perTarget, true);
        }
        if (!perTarget.HasManagerSettingsForBuildTarget(BuildTargetGroup.Android))
        {
            perTarget.CreateDefaultManagerSettingsForBuildTarget(BuildTargetGroup.Android);
        }
        XRGeneralSettings general = perTarget.SettingsForBuildTarget(BuildTargetGroup.Android);
        bool assigned = XRPackageMetadataStore.AssignLoader(general.Manager, ARCoreLoader, BuildTargetGroup.Android);
        general.InitManagerOnStart = initOnStart;
        EditorUtility.SetDirty(general);
        EditorUtility.SetDirty(general.Manager);
        EditorUtility.SetDirty(perTarget);
        AssetDatabase.SaveAssets();
        Debug.Log($"[ARSetup] ARCore loader Android: {(assigned ? "asignado" : "ya estaba")} | iniciar XR al arrancar: {initOnStart}");
    }

    /// Usa XROriginCreateUtil (interno de AR Foundation) por reflexion; si no
    /// existe, arma el XR Origin con los mismos bindings que el oficial.
    private static XROrigin CreateOfficialXROrigin()
    {
        var util = System.Type.GetType("UnityEditor.XR.ARFoundation.XROriginCreateUtil, Unity.XR.ARFoundation.Editor");
        var method = util?.GetMethod("CreateXROriginWithParent",
            System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
        if (method != null)
        {
            var created = method.Invoke(null, new object[] { null }) as XROrigin;
            if (created != null)
            {
                Debug.Log("[ARSetup] XR Origin creado con XROriginCreateUtil de AR Foundation");
                return created;
            }
        }

        var originGo = new GameObject("XR Origin");
        var origin = originGo.AddComponent<XROrigin>();
        var offset = new GameObject("Camera Offset");
        offset.transform.SetParent(originGo.transform, false);
        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        camGo.transform.SetParent(offset.transform, false);
        var cam = camGo.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.black;
        camGo.AddComponent<AudioListener>();
        camGo.AddComponent<ARCameraManager>();
        camGo.AddComponent<ARCameraBackground>();
        var pose = camGo.AddComponent<TrackedPoseDriver>();
        var positionAction = new InputAction("Position", binding: "<XRHMD>/centerEyePosition", expectedControlType: "Vector3");
        positionAction.AddBinding("<HandheldARInputDevice>/devicePosition");
        var rotationAction = new InputAction("Rotation", binding: "<XRHMD>/centerEyeRotation", expectedControlType: "Quaternion");
        rotationAction.AddBinding("<HandheldARInputDevice>/deviceRotation");
        pose.positionInput = new InputActionProperty(positionAction);
        pose.rotationInput = new InputActionProperty(rotationAction);
        origin.Camera = cam;
        origin.CameraFloorOffsetObject = offset;
        Debug.Log("[ARSetup] XR Origin creado manualmente (respaldo)");
        return origin;
    }

    /// Prefab de plano detectado: malla semitransparente (Sprites/Default, siempre incluido).
    private static GameObject CreatePlanePrefab()
    {
        const string dir = "Assets/AR";
        const string prefabPath = dir + "/ARPlaneVisual.prefab";
        const string matPath = dir + "/ARPlaneMat.mat";
        Directory.CreateDirectory(dir);
        var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat == null)
        {
            mat = new Material(Shader.Find("Sprites/Default")) { color = new Color(1f, 0.75f, 0.2f, 0.25f) };
            AssetDatabase.CreateAsset(mat, matPath);
        }
        var go = new GameObject("ARPlaneVisual");
        go.AddComponent<ARPlane>();
        go.AddComponent<MeshFilter>();
        go.AddComponent<MeshRenderer>().sharedMaterial = mat;
        go.AddComponent<MeshCollider>();
        go.AddComponent<ARPlaneMeshVisualizer>();
        var prefab = PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
        Object.DestroyImmediate(go);
        return prefab;
    }

    /// Ancho impreso del marcador (scripts/generar_marcador_ar.py, MARKER_WIDTH_M).
    public const float MarkerWidth = ARSetupConstants.MarkerWidth;
    private const string MarkerTexturePath = "Assets/AR/Marcador_E1_260.png";
    private const string LibraryPath = "Assets/AR/MarcadorLibrary.asset";

    /// XRReferenceImageLibrary con el marcador y su tamano fisico (ARCore lo
    /// usa para que la pose de la imagen salga en metros reales).
    private static XRReferenceImageLibrary CreateReferenceLibrary()
    {
        var importer = (TextureImporter)AssetImporter.GetAtPath(MarkerTexturePath);
        if (importer == null) throw new FileNotFoundException("Generar primero el marcador: python scripts/generar_marcador_ar.py", MarkerTexturePath);
        importer.isReadable = true;
        importer.textureCompression = TextureImporterCompression.Uncompressed;
        importer.mipmapEnabled = false;
        importer.npotScale = TextureImporterNPOTScale.None;
        importer.SaveAndReimport();
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(MarkerTexturePath);

        AssetDatabase.DeleteAsset(LibraryPath);
        var library = ScriptableObject.CreateInstance<XRReferenceImageLibrary>();
        AssetDatabase.CreateAsset(library, LibraryPath);
        library.Add();
        library.SetTexture(0, texture, false);
        library.SetName(0, ARImageAnchor.MarkerName);
        library.SetSpecifySize(0, true);
        library.SetSize(0, new Vector2(MarkerWidth, MarkerWidth));
        EditorUtility.SetDirty(library);
        AssetDatabase.SaveAssets();
        Debug.Log($"[ARSetup] Libreria de imagenes: {ARImageAnchor.MarkerName} {MarkerWidth * 100f:0} cm");
        return library;
    }

    public static void CreateARScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        var light = new GameObject("Directional Light").AddComponent<Light>();
        light.type = LightType.Directional;
        light.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        var sessionGo = new GameObject("AR Session");
        sessionGo.AddComponent<ARSession>();
        sessionGo.AddComponent<ARInputManager>();

        // XR Origin igual al del menu GameObject/XR/XR Origin (Mobile AR) de AR Foundation
        // (camara con ARCameraManager, ARCameraBackground y TrackedPoseDriver configurado).
        XROrigin origin = CreateOfficialXROrigin();
        GameObject originGo = origin.gameObject;
        Camera cam = origin.Camera;
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 300f;   // modo 1:1: el edificio completo mide ~80 m

        // Planos (diagnostico del tracking), raycast y anchors
        var planeManager = originGo.AddComponent<ARPlaneManager>();
        planeManager.planePrefab = CreatePlanePrefab();
        originGo.AddComponent<ARRaycastManager>();
        originGo.AddComponent<ARAnchorManager>();

        // Imagen de referencia (fase 2): se desactiva para asignar la libreria antes de OnEnable
        originGo.SetActive(false);
        var imageManager = originGo.AddComponent<ARTrackedImageManager>();
        imageManager.referenceLibrary = CreateReferenceLibrary();
        imageManager.requestedMaxNumberOfMovingImages = 1;
        originGo.SetActive(true);

        var app = new GameObject("AR App");
        app.AddComponent<ARBootstrap>();
        app.AddComponent<ARImageAnchor>();
        app.AddComponent<ARStructure>();
        app.AddComponent<ARResultsPanel>();

        Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
        EditorSceneManager.SaveScene(scene, ScenePath);
        Debug.Log("[ARSetup] Escena creada: " + ScenePath);
    }
}
