using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Semana 6 · Fase 3: dibuja la estructura (o el sector de E1_260) sobre el
/// anchor de la imagen, transformando coordenadas OpenSees -> AR.
///
///   p_AR (mundo) = T_anchor · ( s · M · (p_OpenSees − p_ref) )
///
///   p_OpenSees : nodo del modelo (x, y, z), z hacia arriba, metros.
///   p_ref      : punto del modelo que coincide con el centro de la imagen.
///   M          : cambio de ejes modelo -> ejes de la imagen (x derecha,
///                y normal saliendo de la imagen, z hacia el borde superior).
///                  marcador en la columna (vertical): (dx, −dy, dz)
///                  marcador en la mesa (horizontal):  (dx,  dz, dy)
///                Ambos tienen det = −1: pasan de un sistema de mano derecha
///                (OpenSees) a uno de mano izquierda (Unity), igual que el
///                viewer (x, z, y).
///   s          : escala (1 = 1:1, 0.01 = maqueta 1:100).
///   T_anchor   : pose del ARAnchor (rotacion + traslacion en el mundo AR),
///                la calcula ARCore en el telefono.
/// </summary>
public class ARStructure : MonoBehaviour
{
    public enum Mode { Columna1a1, Maqueta100, SobrePlano }

    public const string AnchorTag = "E1_260";
    /// Elementos revisados en detalle: siempre se dibujan (tambien fuera del sector en 1:1) y tienen acceso directo.
    public static readonly string[] FeaturedTags = { "E1_260", "E1_72" };

    // Marcador pegado en la cara −Y de la columna E1_260 (x = 10, y = 0, COL70/70),
    // con su centro a 1,20 m del piso terminado (z = 0).
    public static readonly Vector3 MarkerOnColumn = new Vector3(10f, -0.35f, 1.20f);
    public const float SectorXMin = 5f, SectorXMax = 15f, SectorYMin = -7.25f, SectorYMax = 5f;
    public const float SectorZMin = 0f, SectorZMax = 7.92f;

    // Dibujo de la planta en el marcador (mismos parametros que scripts/generar_marcador_ar.py)
    private const float MarkerPx = 1600f, PlanMarginTop = 230f, PlanMargin = 110f, PlanBottomBand = 160f;

    public Mode mode = Mode.Columna1a1;
    public static ARStructure Instance { get; private set; }
    public Transform ModelRoot { get; private set; }
    public float Scale { get; private set; } = 1f;
    public Vector3 RefPoint { get; private set; }
    public ElementData Selected { get; set; }
    public event System.Action Rebuilt;

    private readonly Dictionary<int, NodeData> nodes = new Dictionary<int, NodeData>();
    private readonly Dictionary<int, Renderer> renderers = new Dictionary<int, Renderer>();
    private readonly List<Transform> labels = new List<Transform>();
    private Transform contentRoot;
    private Font labelFont;
    private Material matColumn, matBeam, matBrace, matAnchor, matSelected, matText;
    private Vector2 planCenter;
    private float planScale;   // m de dibujo por m de modelo (modo SobrePlano)

    private void Awake()
    {
        Instance = this;
    }

    private void Start()
    {
        LoadModel();
        if (ARImageAnchor.Instance != null) ARImageAnchor.Instance.Anchored += OnAnchored;
    }

    private void LoadModel()
    {
        if (UnityData.Structure == null)
        {
            var json = Resources.Load<TextAsset>("estructura_p1l4_unity");
            if (json == null) { Debug.LogError("[ARStructure] Falta Resources/estructura_p1l4_unity.json"); return; }
            UnityData.LoadData(JsonUtility.FromJson<StructureData>(json.text));
        }
        nodes.Clear();
        float xmin = float.MaxValue, xmax = float.MinValue, ymin = float.MaxValue, ymax = float.MinValue;
        foreach (NodeData n in UnityData.Structure.nodes)
        {
            nodes[n.id] = n;
            xmin = Mathf.Min(xmin, n.x); xmax = Mathf.Max(xmax, n.x);
            ymin = Mathf.Min(ymin, n.y); ymax = Mathf.Max(ymax, n.y);
        }
        // misma escala y centro del dibujo que generar_marcador_ar.py
        float sx = (MarkerPx - 2f * PlanMargin) / (xmax - xmin);
        float sy = (MarkerPx - PlanMarginTop - PlanMargin - PlanBottomBand) / (ymax - ymin);
        float pxPerM = Mathf.Min(sx, sy);
        planScale = pxPerM * ARSetupConstants.MarkerWidth / MarkerPx;
        float planCenterPxY = PlanMarginTop + (MarkerPx - PlanMarginTop - PlanMargin - PlanBottomBand) / 2f;
        // el centro de la planta queda (MarkerPx/2 − planCenterPxY) px sobre el centro de la imagen
        float upOffsetM = (MarkerPx / 2f - planCenterPxY) / pxPerM;
        planCenter = new Vector2((xmax + xmin) / 2f, (ymax + ymin) / 2f - upOffsetM);

        labelFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        Shader lit = Shader.Find("Standard") ?? Shader.Find("Unlit/Color");
        matColumn = new Material(lit) { color = new Color(0.30f, 0.62f, 0.95f) };
        matBeam = new Material(lit) { color = new Color(0.78f, 0.80f, 0.84f) };
        matBrace = new Material(lit) { color = new Color(0.55f, 0.85f, 0.55f) };
        matAnchor = new Material(lit) { color = new Color(1f, 0.55f, 0.1f) };
        matSelected = new Material(lit) { color = new Color(1f, 0.92f, 0.2f) };
    }

    private void OnAnchored(Transform root)
    {
        contentRoot = root;
        Rebuild();
    }

    public void SetMode(Mode m)
    {
        if (mode == m && ModelRoot != null) return;
        mode = m;
        Rebuild();
    }

    /// Cambio de ejes M (modelo -> ejes de la imagen), sin escala.
    public Vector3 AxesToImage(Vector3 d)
    {
        return mode == Mode.Columna1a1 ? new Vector3(d.x, -d.y, d.z) : new Vector3(d.x, d.z, d.y);
    }

    /// Punto del modelo (OpenSees) -> coordenadas locales del anchor: s · M · (p − p_ref).
    public Vector3 ModelToAnchor(Vector3 p)
    {
        return Scale * AxesToImage(p - RefPoint);
    }

    /// Direccion vertical del modelo (+z OpenSees) en ejes de la imagen.
    public Vector3 ModelUpLocal => AxesToImage(new Vector3(0f, 0f, 1f));

    public Vector3 NodePos(int id)
    {
        NodeData n = nodes[id];
        return new Vector3(n.x, n.y, n.z);
    }

    public bool InSector(ElementData e)
    {
        foreach (int id in new[] { e.nodeI, e.nodeJ })
        {
            NodeData n = nodes[id];
            if (n.x < SectorXMin - 0.01f || n.x > SectorXMax + 0.01f || n.y < SectorYMin - 0.01f || n.y > SectorYMax + 0.01f ||
                n.z < SectorZMin - 0.01f || n.z > SectorZMax + 0.01f) return false;
        }
        return true;
    }

    public void Rebuild()
    {
        if (contentRoot == null || UnityData.Structure == null) return;
        if (ModelRoot != null) Destroy(ModelRoot.gameObject);
        renderers.Clear();
        labels.Clear();

        switch (mode)
        {
            case Mode.Columna1a1: Scale = 1f; RefPoint = MarkerOnColumn; break;
            case Mode.Maqueta100: Scale = 0.01f; RefPoint = new Vector3(planCenter.x, planCenter.y, 0f); break;
            default: Scale = planScale; RefPoint = new Vector3(planCenter.x, planCenter.y, 0f); break;
        }

        ModelRoot = new GameObject("Modelo AR (" + mode + ")").transform;
        ModelRoot.SetParent(contentRoot, false);

        bool sectorOnly = mode == Mode.Columna1a1;
        // seccion minima visible: en maqueta las vigas de 0,6 m quedarian de 6 mm o menos
        float minSection = mode == Mode.Columna1a1 ? 0f : 0.003f;
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (!nodes.ContainsKey(e.nodeI) || !nodes.ContainsKey(e.nodeJ)) continue;
            bool featured = System.Array.IndexOf(FeaturedTags, e.elementTag) >= 0;
            if (sectorOnly && !InSector(e) && !featured) continue;
            Vector3 a = ModelToAnchor(NodePos(e.nodeI));
            Vector3 b = ModelToAnchor(NodePos(e.nodeJ));
            float w = Mathf.Max(minSection, Scale * Mathf.Max(0.15f, e.width_m));
            float h = Mathf.Max(minSection, Scale * Mathf.Max(0.15f, e.height_m));
            if (mode == Mode.SobrePlano) { w = Mathf.Max(w, 0.0025f); h = Mathf.Max(h, 0.0025f); }
            Renderer r = MakeBar(e, a, b, w, h);
            renderers[e.id] = r;

            bool isAnchor = e.elementTag == AnchorTag;
            if (sectorOnly || isAnchor || featured)
            {
                float textH = sectorOnly ? 0.12f : 0.006f;
                AddLabel(e.elementTag, (a + b) * 0.5f + ModelUpLocal * textH * 0.6f, textH, isAnchor);
            }
        }
        RefreshColors();
        Rebuilt?.Invoke();
    }

    private Renderer MakeBar(ElementData e, Vector3 a, Vector3 b, float w, float h)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = e.elementTag;
        go.transform.SetParent(ModelRoot, false);
        Vector3 d = b - a;
        float len = d.magnitude;
        go.transform.localPosition = (a + b) * 0.5f;
        if (len > 1e-6f)
        {
            // alto de la seccion en la vertical del modelo; en columnas, el ancho segun +x del modelo
            Vector3 up = Mathf.Abs(Vector3.Dot(d / len, ModelUpLocal)) > 0.95f ? AxesToImage(Vector3.right) : ModelUpLocal;
            go.transform.localRotation = Quaternion.LookRotation(d / len, up);
        }
        go.transform.localScale = new Vector3(w, h, len);
        go.AddComponent<ARElementTag>().element = e;
        return go.GetComponent<Renderer>();
    }

    private void AddLabel(string text, Vector3 localPos, float height, bool highlight)
    {
        var go = new GameObject("Tag " + text);
        go.transform.SetParent(ModelRoot, false);
        go.transform.localPosition = localPos;
        var tm = go.AddComponent<TextMesh>();
        tm.text = text;
        tm.font = labelFont;
        tm.fontSize = 64;
        tm.characterSize = height / 6.4f;   // alto aprox. de la letra = characterSize * fontSize / 10
        tm.anchor = TextAnchor.LowerCenter;
        tm.color = highlight ? new Color(1f, 0.7f, 0.2f) : Color.white;
        go.GetComponent<MeshRenderer>().material = labelFont.material;
        labels.Add(go.transform);
    }

    public void RefreshColors()
    {
        foreach (var kv in renderers)
        {
            ElementData e = kv.Value.GetComponent<ARElementTag>().element;
            Material m = e == Selected ? matSelected
                : e.elementTag == AnchorTag ? matAnchor
                : e.type == "columna" ? matColumn
                : e.type == "viga" ? matBeam : matBrace;
            kv.Value.sharedMaterial = m;
        }
    }

    public ElementData FindByTag(string tag)
    {
        if (UnityData.Structure == null) return null;
        foreach (ElementData e in UnityData.Structure.elements) if (e.elementTag == tag) return e;
        return null;
    }

    private void LateUpdate()
    {
        // etiquetas siempre mirando a la camara
        Camera cam = Camera.main;
        if (cam == null) return;
        foreach (Transform t in labels)
        {
            if (t != null) t.rotation = Quaternion.LookRotation(t.position - cam.transform.position, cam.transform.up);
        }
    }
}

/// Une cada barra dibujada con su ElementData (id y elementTag de OpenSees).
public class ARElementTag : MonoBehaviour
{
    public ElementData element;
}

/// Constantes compartidas con el editor (ARSetup.MarkerWidth).
public static class ARSetupConstants
{
    public const float MarkerWidth = 0.20f;
}
