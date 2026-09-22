using System.Collections.Generic;
using UnityEngine;

[ExecuteAlways]
public class StructureViewer : MonoBehaviour
{
    [Header("Datos exportados desde OpenSeesPy")]
    public TextAsset structureJson;

    [Header("Apariencia")]
    public float elementRadius = 0.06f;
    public float wallScale = 1.6f;
    public Material beamMaterial;
    public Material columnMaterial;
    public Material supportMaterial;

    private Material defaultBeamMaterial;
    private Material defaultColumnMaterial;
    private Material defaultSupportMaterial;
    private Material defaultWallMaterial;
    private Material defaultDiaphragmMaterial;

    private readonly Dictionary<int, Vector3> nodes = new Dictionary<int, Vector3>();
    private readonly List<ElementSelectable> selectables = new List<ElementSelectable>();
    private DiagramController diagramController;
    private bool structureCreated;

    // Grupos de objetos para los toggles
    private readonly List<GameObject> columnObjects = new List<GameObject>();
    private readonly List<GameObject> beamObjects = new List<GameObject>();
    private readonly List<GameObject> wallObjects = new List<GameObject>();
    private readonly List<GameObject> supportObjects = new List<GameObject>();
    private readonly List<GameObject> diaphragmObjects = new List<GameObject>();
    private readonly List<GameObject> nodeMarkerObjects = new List<GameObject>();
    private readonly List<GameObject> idLabelObjects = new List<GameObject>();
    private readonly List<GameObject> localAxisObjects = new List<GameObject>();
    private readonly Dictionary<string, TributaryFloorData> tributaryFloors =
        new Dictionary<string, TributaryFloorData>();

    // Estados de los toggles
    private bool showColumns = true;
    private bool showBeams = true;
    private bool showWalls = true;
    private bool showSupports = true;
    private bool showDiaphragms = true;
    private bool showNodeMarkers = false;
    private bool showIds = false;
    private bool showLocalAxes = false;

    private string pickerText = "Toca o haz click sobre una barra.";

    private void Start()
    {
        CreateStructure();
    }

    private void OnEnable()
    {
        CreateStructure();
    }

    private void CreateStructure()
    {
        CreateDefaultMaterials();

        if (structureCreated)
        {
            return;
        }

        if (structureJson == null)
        {
            structureJson = Resources.Load<TextAsset>("estructura_gravedad_unity");
            if (structureJson == null)
            {
                Debug.LogError("Asigna estructura_gravedad_unity.json en el campo Structure Json o copialo a Assets/Resources.");
                return;
            }
        }

        StructureData data = JsonUtility.FromJson<StructureData>(structureJson.text);
        if (data.tributaryList != null)
        {
            foreach (TributaryFloorData td in data.tributaryList)
            {
                tributaryFloors[td.piso] = td;
            }
        }

        ClearStructureChildren();
        nodes.Clear();
        selectables.Clear();
        columnObjects.Clear();
        beamObjects.Clear();
        wallObjects.Clear();
        supportObjects.Clear();
        diaphragmObjects.Clear();
        nodeMarkerObjects.Clear();
        idLabelObjects.Clear();
        localAxisObjects.Clear();

        CreateNodes(data);
        CreateColumnAndBeamElements(data);
        CreateWalls(data);
        CreateDiaphragms(data);
        CreateSupports(data);
        CreatePointLoads(data);
        CreateGlobalAxes();
        CreateDiagramController();
        structureCreated = true;
        RefreshVisibility();
    }

    private void ClearStructureChildren()
    {
        for (int i = transform.childCount - 1; i >= 0; i--)
        {
            GameObject child = transform.GetChild(i).gameObject;
            if (Application.isPlaying)
            {
                Destroy(child);
            }
            else
            {
                DestroyImmediate(child);
            }
        }
    }

    private void CreateNodes(StructureData data)
    {
        foreach (NodeData node in data.nodes)
        {
            nodes[node.id] = ToUnity(node);
        }
    }

    private void CreateColumnAndBeamElements(StructureData data)
    {
        foreach (ElementData element in data.elements)
        {
            if (!nodes.ContainsKey(element.nodeI) || !nodes.ContainsKey(element.nodeJ))
            {
                continue;
            }

            Vector3 start = nodes[element.nodeI];
            Vector3 end = nodes[element.nodeJ];
            Vector3 midpoint = (start + end) * 0.5f;
            Vector3 direction = end - start;

            GameObject cylinder = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            cylinder.name = $"Elemento_{element.id}_{element.type}";
            cylinder.transform.SetParent(transform);
            cylinder.transform.position = midpoint;
            cylinder.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction.normalized);
            cylinder.transform.localScale = new Vector3(elementRadius, direction.magnitude * 0.5f, elementRadius);

            Renderer renderer = cylinder.GetComponent<Renderer>();
            bool isColumn = element.type == "columna";
            renderer.material = isColumn ? ColumnMaterial() : BeamMaterial();
            (isColumn ? columnObjects : beamObjects).Add(cylinder);

            ElementSelectable selectable = cylinder.AddComponent<ElementSelectable>();
            selectable.data = element;
            selectable.startPoint = start;
            selectable.endPoint = end;
            selectables.Add(selectable);
        }
    }

    private void CreateWalls(StructureData data)
    {
        if (data.walls == null)
        {
            return;
        }

        foreach (WallData wall in data.walls)
        {
            if (!nodes.ContainsKey(wall.nodeI) || !nodes.ContainsKey(wall.nodeJ))
            {
                continue;
            }

            Vector3 start = nodes[wall.nodeI];
            Vector3 end = nodes[wall.nodeJ];
            Vector3 midpoint = (start + end) * 0.5f;
            Vector3 direction = end - start;

            GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = $"Muro_{wall.id}";
            box.transform.SetParent(transform);
            box.transform.position = midpoint;
            box.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction.normalized);
            float thick = Mathf.Max(wall.grosor, 0.01f);
            box.transform.localScale = new Vector3(thick * wallScale, direction.magnitude / 2f, wall.longitud);
            box.GetComponent<Renderer>().material = WallMaterial();
            wallObjects.Add(box);

            ElementSelectable selectable = box.AddComponent<ElementSelectable>();
            selectable.startPoint = start;
            selectable.endPoint = end;
            selectable.customLabel = $"Muro {wall.id} (equivalente)\n" +
                                     $"Grosor: {wall.grosor:0.##} m | Largo: {wall.longitud:0.##} m\n" +
                                     $"Tramo: {wall.bottom} -> {wall.top}";
            selectables.Add(selectable);
        }
    }

    private void CreateDiaphragms(StructureData data)
    {
        if (data.diaphragmList == null)
        {
            return;
        }

        // Si el JSON trae las losas reales (paneles), dibujar la huella real.
        if (data.slabs != null && data.slabs.Length > 0)
        {
            CreateSlabPanels(data);
            return;
        }

        Bounds bounds = GetStructureBounds();
        float px = Mathf.Max(bounds.size.x, Mathf.Abs(bounds.min.x), Mathf.Abs(bounds.max.x));
        float py = Mathf.Max(bounds.size.y, Mathf.Abs(bounds.min.z), Mathf.Abs(bounds.max.z));

        foreach (DiaphragmData dia in data.diaphragmList)
        {
            Vector3 center = new Vector3(dia.x, dia.z, dia.y);

            GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Cube);
            plane.name = $"Diafragma_{dia.level}_{dia.maestro}";
            plane.transform.SetParent(transform);
            plane.transform.position = center;
            plane.transform.localScale = new Vector3(px * 2f, 0.02f, py * 2f);
            plane.GetComponent<Renderer>().material = DiaphragmMaterial();
            diaphragmObjects.Add(plane);
        }
    }

    private void CreateSlabPanels(StructureData data)
    {
        float thickness = 0.02f;
        foreach (SlabData slab in data.slabs)
        {
            float cx = (slab.x0 + slab.x1) * 0.5f;
            float cy = (slab.y0 + slab.y1) * 0.5f;
            float dx = Mathf.Abs(slab.x1 - slab.x0);
            float dy = Mathf.Abs(slab.y1 - slab.y0);
            if (dx <= 0.001f || dy <= 0.001f)
            {
                continue;
            }

            Vector3 center = new Vector3(cx, slab.z, cy);

            GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Cube);
            plane.name = $"Losa_{slab.id}_{slab.nivel}";
            plane.transform.SetParent(transform);
            plane.transform.position = center;
            plane.transform.localScale = new Vector3(dx, thickness, dy);
            plane.GetComponent<Renderer>().material = DiaphragmMaterial();
            diaphragmObjects.Add(plane);
        }
    }

    private Bounds GetStructureBounds()
    {
        Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
        bool first = true;
        foreach (Vector3 p in nodes.Values)
        {
            if (first)
            {
                bounds = new Bounds(p, Vector3.zero);
                first = false;
            }
            else
            {
                bounds.Encapsulate(p);
            }
        }
        return bounds;
    }

    private void CreateDiagramController()
    {
        diagramController = gameObject.AddComponent<DiagramController>();
        diagramController.Initialize(selectables);
    }

    private void CreateSupports(StructureData data)
    {
        if (data.supports == null || data.supports.Length == 0)
        {
            return;
        }

        foreach (SupportData supportData in data.supports)
        {
            if (!nodes.ContainsKey(supportData.node))
            {
                continue;
            }

            CreateSupportSymbol(supportData);
        }
    }

    private void CreateSupportSymbol(SupportData supportData)
    {
        Vector3 node = nodes[supportData.node];

        GameObject support = GameObject.CreatePrimitive(PrimitiveType.Cube);
        support.name = $"Apoyo_Empotrado_N{supportData.node}";
        support.transform.SetParent(transform);
        support.transform.position = node + Vector3.down * 0.08f;
        support.transform.localScale = new Vector3(0.55f, 0.14f, 0.55f);
        support.GetComponent<Renderer>().material = SupportMaterial();
        supportObjects.Add(support);
        CreateSupportLabel(supportData, "Empotrado", node);
    }

    private void CreateSupportLabel(SupportData supportData, string label, Vector3 node)
    {
        GameObject labelObject = new GameObject($"Etiqueta_Apoyo_N{supportData.node}");
        labelObject.transform.SetParent(transform);
        labelObject.transform.position = node + new Vector3(0.15f, 0.25f, 0.15f);

        TextMesh text = labelObject.AddComponent<TextMesh>();
        text.text = $"N{supportData.node}\n{label}";
        text.characterSize = 0.18f;
        text.anchor = TextAnchor.MiddleCenter;
        text.color = Color.yellow;
        supportObjects.Add(labelObject);
    }

    private void CreatePointLoads(StructureData data)
    {
        if (data.pointLoads == null)
        {
            return;
        }

        foreach (PointLoadData load in data.pointLoads)
        {
            if (!nodes.ContainsKey(load.node) || Mathf.Abs(load.fz) < 0.001f)
            {
                continue;
            }

            Vector3 node = nodes[load.node];
            float sign = load.fz < 0f ? -1f : 1f;
            Vector3 start = node + Vector3.up * sign * 0.9f;
            Vector3 end = node + Vector3.up * sign * 0.15f;
            Vector3 direction = end - start;

            GameObject arrow = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            arrow.name = $"Carga_Puntual_N{load.node}";
            arrow.transform.SetParent(transform);
            arrow.transform.position = (start + end) * 0.5f;
            arrow.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction.normalized);
            arrow.transform.localScale = new Vector3(0.035f, direction.magnitude * 0.5f, 0.035f);
            arrow.GetComponent<Renderer>().material = CreateMaterial(Color.red);

            GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            head.name = $"Punta_Carga_N{load.node}";
            head.transform.SetParent(transform);
            head.transform.position = end;
            head.transform.localScale = new Vector3(0.18f, 0.18f, 0.18f);
            head.GetComponent<Renderer>().material = CreateMaterial(Color.red);
        }
    }

    private void CreateGlobalAxes()
    {
        CreateAxis("X global", Vector3.zero, Vector3.right, Color.red);
        CreateAxis("Y global", Vector3.zero, Vector3.forward, Color.green);
        CreateAxis("Z global", Vector3.zero, Vector3.up, Color.blue);
    }

    private void CreateAxis(string name, Vector3 start, Vector3 direction, Color color)
    {
        GameObject axis = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        axis.name = name;
        axis.transform.SetParent(transform);
        axis.transform.position = start + direction * 0.5f;
        axis.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction);
        axis.transform.localScale = new Vector3(0.025f, 0.5f, 0.025f);

        Renderer renderer = axis.GetComponent<Renderer>();
        renderer.material = CreateMaterial(color);
    }

    // Metodos de visualizacion opcional (nodulos, IDs, ejes locales)
    public void SetNodeMarkersVisible(bool visible)
    {
        if (visible && nodeMarkerObjects.Count == 0)
        {
            CreateNodeMarkers();
        }
        showNodeMarkers = visible;
        RefreshVisibility();
    }

    private void CreateNodeMarkers()
    {
        foreach (KeyValuePair<int, Vector3> kv in nodes)
        {
            GameObject marker = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            marker.name = $"Nodo_{kv.Key}";
            marker.transform.SetParent(transform);
            marker.transform.position = kv.Value;
            marker.transform.localScale = new Vector3(0.14f, 0.14f, 0.14f);
            marker.GetComponent<Renderer>().material = CreateMaterial(new Color(0.2f, 0.9f, 0.4f));
            nodeMarkerObjects.Add(marker);
        }
    }

    public void SetIdsVisible(bool visible)
    {
        if (visible && idLabelObjects.Count == 0)
        {
            CreateIdLabels();
        }
        showIds = visible;
        RefreshVisibility();
    }

    private void CreateIdLabels()
    {
        foreach (KeyValuePair<int, Vector3> kv in nodes)
        {
            GameObject labelObject = new GameObject($"Label_Nodo_{kv.Key}");
            labelObject.transform.SetParent(transform);
            labelObject.transform.position = kv.Value + new Vector3(0, 0.35f, 0);

            TextMesh text = labelObject.AddComponent<TextMesh>();
            text.text = kv.Key.ToString();
            text.characterSize = 0.14f;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = Color.cyan;
            idLabelObjects.Add(labelObject);
        }

        foreach (ElementSelectable sel in selectables)
        {
            if (sel.customLabel != null)
            {
                continue;
            }
            GameObject labelObject = new GameObject($"Label_Ele_{sel.data.id}");
            labelObject.transform.SetParent(transform);
            Vector3 mid = (sel.startPoint + sel.endPoint) * 0.5f;
            labelObject.transform.position = mid + new Vector3(0, 0.3f, 0);

            TextMesh text = labelObject.AddComponent<TextMesh>();
            text.text = sel.data.id.ToString();
            text.characterSize = 0.12f;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = Color.white;
            idLabelObjects.Add(labelObject);
        }
    }

    public void SetLocalAxesVisible(bool visible)
    {
        if (visible && localAxisObjects.Count == 0)
        {
            CreateLocalAxes();
        }
        showLocalAxes = visible;
        RefreshVisibility();
    }

    private void CreateLocalAxes()
    {
        foreach (ElementSelectable sel in selectables)
        {
            if (sel.customLabel != null)
            {
                continue;
            }
            Vector3 mid = (sel.startPoint + sel.endPoint) * 0.5f;
            Vector3 dir = (sel.endPoint - sel.startPoint).normalized;
            Vector3 perp = Vector3.Cross(dir, Vector3.up).normalized;
            if (perp.sqrMagnitude < 0.01f)
            {
                perp = Vector3.right;
            }
            GameObject localAxis = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            localAxis.name = $"EjeLocal_E{sel.data.id}";
            localAxis.transform.SetParent(transform);
            localAxis.transform.position = mid + dir * 0.75f;
            localAxis.transform.rotation = Quaternion.FromToRotation(Vector3.up, dir);
            localAxis.transform.localScale = new Vector3(0.02f, 0.75f, 0.02f);
            localAxis.GetComponent<Renderer>().material = CreateMaterial(Color.magenta);
            localAxisObjects.Add(localAxis);
        }
    }

    private void RefreshVisibility()
    {
        SetGroupVisible(columnObjects, showColumns);
        SetGroupVisible(beamObjects, showBeams);
        SetGroupVisible(wallObjects, showWalls);
        SetGroupVisible(supportObjects, showSupports);
        SetGroupVisible(diaphragmObjects, showDiaphragms);
        SetGroupVisible(nodeMarkerObjects, showNodeMarkers);
        SetGroupVisible(idLabelObjects, showIds);
        SetGroupVisible(localAxisObjects, showLocalAxes);
    }

    private void SetGroupVisible(List<GameObject> group, bool visible)
    {
        foreach (GameObject go in group)
        {
            if (go != null)
            {
                go.SetActive(visible);
            }
        }
    }

    private void OnGUI()
    {
        int y0 = 20;
        GUI.Box(new Rect(20, y0, 330, 40), "UANDES - Modelo estructural de gravedad");
        y0 += 44;

        showColumns = GUI.Toggle(new Rect(20, y0, 150, 24), showColumns, "Columnas");
        showBeams = GUI.Toggle(new Rect(180, y0, 150, 24), showBeams, "Vigas");
        y0 += 26;
        showWalls = GUI.Toggle(new Rect(20, y0, 150, 24), showWalls, "Muros equiv.");
        showSupports = GUI.Toggle(new Rect(180, y0, 150, 24), showSupports, "Apoyos");
        y0 += 26;
        showDiaphragms = GUI.Toggle(new Rect(20, y0, 150, 24), showDiaphragms, "Diafragmas");
        showNodeMarkers = GUI.Toggle(new Rect(180, y0, 150, 24), showNodeMarkers, "Nodos");
        y0 += 26;
        showIds = GUI.Toggle(new Rect(20, y0, 150, 24), showIds, "IDs");
        showLocalAxes = GUI.Toggle(new Rect(180, y0, 150, 24), showLocalAxes, "Ejes locales");
        y0 += 40;

        if (GUI.Button(new Rect(20, y0, 310, 26), "Mostrar nodos"))
        {
            SetNodeMarkersVisible(true);
            showNodeMarkers = true;
        }
        y0 += 30;
        if (GUI.Button(new Rect(20, y0, 310, 26), "Mostrar IDs"))
        {
            SetIdsVisible(true);
            showIds = true;
        }
        y0 += 30;
        if (GUI.Button(new Rect(20, y0, 310, 26), "Mostrar ejes locales"))
        {
            SetLocalAxesVisible(true);
            showLocalAxes = true;
        }
        y0 += 40;

        RefreshVisibility();

        string tribText = "Areas tributarias (q_G = 5.1 kN/m2):";
        foreach (KeyValuePair<string, TributaryFloorData> kv in tributaryFloors)
        {
            TributaryFloorData td = kv.Value;
            tribText += $"\n  {kv.Key}: A={td.area_total:0.##} m2  carga={td.carga_total:0.##} kN";
        }
        GUI.Box(new Rect(20, y0, 330, 40 + tributaryFloors.Count * 18), tribText);
    }

    private Vector3 ToUnity(NodeData node)
    {
        return new Vector3(node.x, node.z, node.y);
    }

    private void CreateDefaultMaterials()
    {
        defaultBeamMaterial = CreateMaterial(new Color(0.0f, 0.62f, 0.85f));
        defaultColumnMaterial = CreateMaterial(new Color(0.18f, 0.18f, 0.24f));
        defaultSupportMaterial = CreateMaterial(new Color(0.95f, 0.38f, 0.12f));
        defaultWallMaterial = CreateMaterial(new Color(0.55f, 0.6f, 0.42f));
        defaultDiaphragmMaterial = CreateMaterial(new Color(0.7f, 0.8f, 0.95f, 0.35f));
    }

    private Material CreateMaterial(Color color)
    {
        Shader shader = Shader.Find("Standard");
        if (shader == null)
        {
            shader = Shader.Find("Universal Render Pipeline/Lit");
        }
        if (shader == null)
        {
            shader = Shader.Find("Sprites/Default");
        }

        Material material = new Material(shader);
        material.color = color;
        if (color.a < 1f)
        {
            material.SetFloat("_Mode", 3f);
            material.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            material.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            material.SetInt("_ZWrite", 0);
            material.DisableKeyword("_ALPHATEST_ON");
            material.EnableKeyword("_ALPHABLEND_ON");
            material.renderQueue = 3000;
        }
        return material;
    }

    private Material BeamMaterial()
    {
        return beamMaterial != null ? beamMaterial : defaultBeamMaterial;
    }

    private Material ColumnMaterial()
    {
        return columnMaterial != null ? columnMaterial : defaultColumnMaterial;
    }

    private Material SupportMaterial()
    {
        return supportMaterial != null ? supportMaterial : defaultSupportMaterial;
    }

    private Material WallMaterial()
    {
        return defaultWallMaterial;
    }

    private Material DiaphragmMaterial()
    {
        return defaultDiaphragmMaterial;
    }
}
