using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class MCOCSetup
{
    [InitializeOnLoadMethod]
    public static void CrearVisualizadorSiFalta()
    {
        EditorApplication.delayCall += () =>
        {
            if (GameObject.Find("StructureViewer") != null)
            {
                return;
            }
            CrearVisualizador(false);
        };
    }

    [MenuItem("MCOC/Crear Visualizador")]
    public static void CrearVisualizador()
    {
        CrearVisualizador(true);
    }

    public static void CrearVisualizador(bool showDialog)
    {
        TextAsset json = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Resources/estructura_edificio1_unity.json");
        if (json == null)
        {
            json = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/estructura_3d_unity.json");
        }
        if (json == null)
        {
            if (showDialog && !Application.isBatchMode)
            {
                EditorUtility.DisplayDialog(
                    "Falta JSON",
                    "No se encontro el JSON en Assets/Resources.",
                    "OK");
            }
            return;
        }

        GameObject existing = GameObject.Find("StructureViewer");
        if (existing != null)
        {
            Object.DestroyImmediate(existing);
        }

        GameObject viewerObject = new GameObject("StructureViewer");
        StructureViewer viewer = viewerObject.AddComponent<StructureViewer>();
        viewer.structureJson = json;

        Camera camera = Camera.main;
        if (camera == null)
        {
            GameObject cameraObject = new GameObject("Main Camera");
            cameraObject.tag = "MainCamera";
            camera = cameraObject.AddComponent<Camera>();
        }

        camera.transform.position = new Vector3(8f, 6f, -8f);
        camera.transform.rotation = Quaternion.Euler(35f, -35f, 0f);

        if (camera.GetComponent<ElementPicker>() == null)
        {
            ElementPicker picker = camera.gameObject.AddComponent<ElementPicker>();
            picker.targetCamera = camera;
        }

        if (camera.GetComponent<OrbitCamera>() == null)
        {
            camera.gameObject.AddComponent<OrbitCamera>();
        }

        if (Object.FindObjectOfType<Light>() == null)
        {
            GameObject lightObject = new GameObject("Directional Light");
            Light light = lightObject.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.2f;
            lightObject.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
        }

        Selection.activeGameObject = viewerObject;
        Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), "Assets/Scenes/StructureViewerScene.unity");
        if (showDialog && !Application.isBatchMode)
        {
            EditorUtility.DisplayDialog("Listo", "Visualizador creado. Ahora presiona Play.", "OK");
        }
    }
}
