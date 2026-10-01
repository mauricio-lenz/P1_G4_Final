using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

/// <summary>
/// Semana 6 · Fase 1: verifica que la sesion AR arranque en el telefono.
/// Muestra el estado de ARCore / ARSession, el motivo si se pierde el tracking,
/// la posicion de la camara y los planos detectados. Tocando un plano se coloca
/// un cubo de prueba anclado a ese plano: si el cubo se queda fijo al caminar,
/// el seguimiento (pose del dispositivo) y los anchors funcionan.
/// </summary>
public class ARBootstrap : MonoBehaviour
{
    private string availability = "verificando...";
    private ARRaycastManager raycaster;
    private ARPlaneManager planes;
    private ARAnchorManager anchors;
    private ARCameraManager cameraManager;
    private GameObject testCube;
    private ARAnchor cubeAnchor;
    private int cameraFrames;
    private float frameWindowStart;
    private float cameraFps;
    private static readonly List<ARRaycastHit> Hits = new List<ARRaycastHit>();

    private int imuSensors = -1;

    /// Fuerza el IMU a 200 Hz (ver Plugins/Android/ImuBooster.java).
    private void BoostImu(bool on)
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        try
        {
            using (var booster = new AndroidJavaClass("cl.uandes.mcoc.ImuBooster"))
            {
                if (on)
                {
                    using (var player = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                    using (var activity = player.GetStatic<AndroidJavaObject>("currentActivity"))
                    {
                        imuSensors = booster.CallStatic<int>("start", activity);
                    }
                }
                else
                {
                    booster.CallStatic("stop");
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("[ARBootstrap] ImuBooster: " + e.Message);
        }
#endif
    }

    private void OnApplicationPause(bool paused)
    {
        BoostImu(!paused);
    }

    private void OnDestroy()
    {
        BoostImu(false);
    }

    private IEnumerator Start()
    {
        BoostImu(true);
        raycaster = FindAnyObjectByType<ARRaycastManager>();
        planes = FindAnyObjectByType<ARPlaneManager>();
        anchors = FindAnyObjectByType<ARAnchorManager>();
        cameraManager = FindAnyObjectByType<ARCameraManager>();
        if (cameraManager != null) cameraManager.frameReceived += _ => cameraFrames++;
        frameWindowStart = Time.unscaledTime;

        if (ARSession.state == ARSessionState.None || ARSession.state == ARSessionState.CheckingAvailability)
        {
            yield return ARSession.CheckAvailability();
        }
        availability = ARSession.state == ARSessionState.Unsupported ? "NO compatible con ARCore" : "compatible con ARCore";
    }

    private void Update()
    {
        if (Time.unscaledTime - frameWindowStart >= 1f)
        {
            cameraFps = cameraFrames / (Time.unscaledTime - frameWindowStart);
            cameraFrames = 0;
            frameWindowStart = Time.unscaledTime;
        }

        // toque sobre un plano detectado -> cubo anclado al plano
        if (Input.touchCount == 1 && Input.GetTouch(0).phase == UnityEngine.TouchPhase.Began && raycaster != null)
        {
            Vector2 pos = Input.GetTouch(0).position;
            bool anchored = ARImageAnchor.Instance != null && ARImageAnchor.Instance.HasAnchor;
            bool overPanels = anchored || pos.x / UiTheme.Scale < UiTheme.SideM + 480f;
            if (!overPanels && raycaster.Raycast(pos, Hits, TrackableType.PlaneWithinPolygon))
            {
                PlaceCube(Hits[0]);
            }
        }
    }

    private void PlaceCube(ARRaycastHit hit)
    {
        if (testCube != null) Destroy(testCube);
        if (cubeAnchor != null) Destroy(cubeAnchor.gameObject);

        ARPlane plane = planes != null ? planes.GetPlane(hit.trackableId) : null;
        cubeAnchor = plane != null && anchors != null ? anchors.AttachAnchor(plane, hit.pose) : null;

        testCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        testCube.name = "CuboPrueba_AR";
        testCube.transform.localScale = Vector3.one * 0.15f;
        Shader shader = Shader.Find("Standard") ?? Shader.Find("Unlit/Color");
        testCube.GetComponent<Renderer>().material = new Material(shader) { color = new Color(0.25f, 0.8f, 1f) };
        if (cubeAnchor != null)
        {
            testCube.transform.SetParent(cubeAnchor.transform, false);
            testCube.transform.localPosition = new Vector3(0f, 0.075f, 0f);
        }
        else
        {
            testCube.transform.position = hit.pose.position + Vector3.up * 0.075f;
        }
    }

    private void OnGUI()
    {
        UiTheme.ApplyScale();
        float w = 470f;
        float x = UiTheme.SideM, y = UiTheme.SideM;
        UiTheme.GUIBox(new Rect(x, y, w, 196f), "AR · FASE 1 (sesion y tracking)");
        float ly = y + 28f;
        GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f), $"Dispositivo: {availability} | IMU 200 Hz: {imuSensors} sensores", UiTheme.Label); ly += 20f;
        GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f),
            $"Sesion: {ARSession.state} | motivo: {ARSession.notTrackingReason}", UiTheme.Label); ly += 20f;
        Vector3 p = Camera.main != null ? Camera.main.transform.position : Vector3.zero;
        GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f), $"Camara (m): x={p.x:0.00} y={p.y:0.00} z={p.z:0.00}", UiTheme.Label); ly += 20f;
        int planeCount = planes != null ? planes.trackables.count : 0;
        GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f), $"Planos detectados: {planeCount} | imagen de camara: {cameraFps:0} fps", UiTheme.Label); ly += 22f;
        string hint = testCube != null
            ? "Cubo anclado al plano: camina alrededor; debe quedarse fijo."
            : planeCount > 0 ? "Toca un plano (zona marcada) para colocar el cubo."
            : "Apunta al piso o a una mesa y muevete lento hasta ver planos.";
        GUI.Label(new Rect(x + 12f, ly, w - 24f, 40f), hint, UiTheme.DimLabel);
    }
}
