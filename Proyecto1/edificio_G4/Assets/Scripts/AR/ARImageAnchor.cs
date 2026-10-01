using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

/// <summary>
/// Semana 6 · Fase 2: detecta la imagen de referencia (Marcador_E1_260),
/// lee su pose y crea un ARAnchor en esa pose. Todo el contenido AR se cuelga
/// de <see cref="ContentRoot"/> (hijo del anchor), asi queda fijo en el mundo
/// aunque la imagen deje de verse.
///
/// Ejes de la pose de la imagen (convencion de AR Foundation):
///   x = derecha de la imagen (+X del marcador), z = hacia el borde superior
///   (+Y del marcador), y = normal saliendo de la imagen.
/// </summary>
public class ARImageAnchor : MonoBehaviour
{
    public const string MarkerName = "Marcador_E1_260";

    /// Segundos de tracking continuo antes de anclar (evita anclar con la primera pose, que es ruidosa).
    public float settleTime = 0.6f;

    public static ARImageAnchor Instance { get; private set; }
    public Transform ContentRoot { get; private set; }
    public ARAnchor Anchor { get; private set; }
    public bool HasAnchor => Anchor != null;
    public event System.Action<Transform> Anchored;

    private ARTrackedImageManager images;
    private ARAnchorManager anchors;
    private ARTrackedImage marker;
    private float trackingSince = -1f;
    private bool creating;
    private string status = "buscando la imagen...";
    private Vector2 markerSize;

    private void Awake()
    {
        Instance = this;
    }

    private void Start()
    {
        images = FindAnyObjectByType<ARTrackedImageManager>();
        anchors = FindAnyObjectByType<ARAnchorManager>();
        if (images == null) status = "falta ARTrackedImageManager";
    }

    private void Update()
    {
        if (images == null) return;

        marker = null;
        foreach (ARTrackedImage img in images.trackables)
        {
            if (img.referenceImage.name == MarkerName) { marker = img; break; }
        }

        bool tracking = marker != null && marker.trackingState == TrackingState.Tracking;
        if (!tracking)
        {
            trackingSince = -1f;
            if (!HasAnchor) status = marker == null ? "buscando la imagen..." : "imagen vista, sin tracking (acercate)";
            return;
        }

        if (trackingSince < 0f) trackingSince = Time.unscaledTime;
        markerSize = marker.size;
        if (!HasAnchor && !creating && Time.unscaledTime - trackingSince >= settleTime)
        {
            CreateAnchor();
        }
    }

    /// Crea (o recrea) el anchor en la pose actual de la imagen.
    public async void CreateAnchor()
    {
        if (marker == null || marker.trackingState != TrackingState.Tracking || anchors == null || creating) return;
        creating = true;
        status = "creando anchor...";
        Pose pose = new Pose(marker.transform.position, marker.transform.rotation);

        Result<ARAnchor> result = await anchors.TryAddAnchorAsync(pose);
        creating = false;
        if (!result.status.IsSuccess() || result.value == null)
        {
            status = "no se pudo crear el anchor; reintentando";
            return;
        }

        ARAnchor old = Anchor;
        Anchor = result.value;
        Anchor.name = "Anchor_" + MarkerName;
        if (ContentRoot == null)
        {
            ContentRoot = new GameObject("AR Content").transform;
            BuildMarkerGizmo(ContentRoot, markerSize);
        }
        ContentRoot.SetParent(Anchor.transform, false);
        ContentRoot.localPosition = Vector3.zero;
        ContentRoot.localRotation = Quaternion.identity;
        if (old != null) Destroy(old.gameObject);

        status = "anclado";
        Anchored?.Invoke(ContentRoot);
    }

    // Marco del marcador + ejes x (rojo), y normal (verde), z (azul).
    private static void BuildMarkerGizmo(Transform parent, Vector2 size)
    {
        var gizmo = new GameObject("Marcador (marco y ejes)").transform;
        gizmo.SetParent(parent, false);
        float hx = size.x * 0.5f, hz = size.y * 0.5f;
        Color frame = new Color(1f, 0.78f, 0.35f);
        Line(gizmo, "Marco", frame, 0.006f, true,
            new Vector3(-hx, 0f, -hz), new Vector3(hx, 0f, -hz), new Vector3(hx, 0f, hz), new Vector3(-hx, 0f, hz));
        Line(gizmo, "Eje X", Color.red, 0.008f, false, Vector3.zero, new Vector3(0.12f, 0f, 0f));
        Line(gizmo, "Eje normal", Color.green, 0.008f, false, Vector3.zero, new Vector3(0f, 0.12f, 0f));
        Line(gizmo, "Eje Z", new Color(0.2f, 0.5f, 1f), 0.008f, false, Vector3.zero, new Vector3(0f, 0f, 0.12f));
    }

    public static LineRenderer Line(Transform parent, string name, Color color, float width, bool loop, params Vector3[] points)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var lr = go.AddComponent<LineRenderer>();
        lr.useWorldSpace = false;
        lr.loop = loop;
        lr.positionCount = points.Length;
        lr.SetPositions(points);
        lr.startWidth = lr.endWidth = width;
        lr.material = new Material(Shader.Find("Sprites/Default"));
        lr.startColor = lr.endColor = color;
        lr.numCapVertices = 2;
        return lr;
    }

    private void OnGUI()
    {
        UiTheme.ApplyScale();
        float w = 470f, x = UiTheme.SideM, y = UiTheme.SideM + 206f;
        UiTheme.GUIBox(new Rect(x, y, w, 150f), "AR · FASE 2 (imagen y anchor)");
        float ly = y + 28f;
        GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f), "Imagen " + MarkerName + ": " + status, UiTheme.Label); ly += 20f;
        if (marker != null)
        {
            Vector3 p = marker.transform.position, e = marker.transform.rotation.eulerAngles;
            GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f),
                $"Pose imagen: ({p.x:0.00}, {p.y:0.00}, {p.z:0.00}) m | rot ({e.x:0}, {e.y:0}, {e.z:0})°", UiTheme.Label);
            ly += 20f;
            GUI.Label(new Rect(x + 12f, ly, w - 24f, 20f),
                $"Tamano medido: {marker.size.x * 100f:0.0} x {marker.size.y * 100f:0.0} cm | {marker.trackingState}", UiTheme.Label);
        }
        ly = y + 88f;
        if (HasAnchor)
        {
            float dist = Camera.main != null ? Vector3.Distance(Camera.main.transform.position, Anchor.transform.position) : 0f;
            GUI.Label(new Rect(x + 12f, ly, w - 150f, 20f), $"Anchor: {Anchor.trackingState} | a {dist:0.00} m", UiTheme.Label);
        }
        bool canAnchor = marker != null && marker.trackingState == TrackingState.Tracking && !creating;
        GUI.enabled = canAnchor;
        if (GUI.Button(new Rect(x + w - 132f, y + 108f, 120f, 34f), HasAnchor ? "RE-ANCLAR" : "ANCLAR"))
        {
            CreateAnchor();
        }
        GUI.enabled = true;
    }
}
