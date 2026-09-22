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
    private PMPanel pmPanel;
    private StructureData loadedData;

    // Grupos de objetos para los toggles
    private readonly List<GameObject> columnObjects = new List<GameObject>();
    private readonly List<GameObject> beamObjects = new List<GameObject>();
    private readonly List<GameObject> wallObjects = new List<GameObject>();
    private readonly List<GameObject> supportObjects = new List<GameObject>();
    private readonly List<GameObject> diaphragmObjects = new List<GameObject>();
    private readonly List<GameObject> loadObjects = new List<GameObject>();
    private readonly List<GameObject> nodeMarkerObjects = new List<GameObject>();
    private readonly List<GameObject> idLabelObjects = new List<GameObject>();
    private readonly List<GameObject> localAxisObjects = new List<GameObject>();
    private readonly Dictionary<GameObject, string> objectFloor = new Dictionary<GameObject, string>();
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
    private bool showLoads = false;
    private bool showTributarySummary = false;
    private bool showUtilization = false;
    private readonly Dictionary<GameObject, Color> originalUtilColors = new Dictionary<GameObject, Color>();

    // Combinaciones de carga
    private string[] comboOptions = new string[0];
    private int comboIndex = 0;

    // UI base FASE 1
    private readonly string[] resultOptions = new string[] { "None", "Axial", "Corte", "Momento", "Deformada" };
    private int resultIndex = 0;
    private string[] floorOptions = new string[] { "Todos" };
    private int floorIndex = 0;
    private string statusMessage = "Click sobre un elemento para ver informacion y P-M.";
    private Vector2 leftScroll;

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

        if (structureJson == null)
        {
            structureJson = Resources.Load<TextAsset>("estructura_p1l4_unity");
            if (structureJson == null)
            {
                structureJson = Resources.Load<TextAsset>("estructura_completo_unity");
            }
            if (structureJson == null)
            {
                Debug.LogError("Asigna estructura_p1l4_unity.json (o estructura_completo_unity.json) a Assets/Resources.");
                return;
            }
        }

        loadedData = JsonUtility.FromJson<StructureData>(structureJson.text);
        UnityData.LoadData(loadedData);

        if (loadedData.tributaryList != null)
        {
            foreach (TributaryFloorData td in loadedData.tributaryList)
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
        loadObjects.Clear();
        objectFloor.Clear();

        CreateNodes(loadedData);
        CreateColumnAndBeamElements(loadedData);
        CreateWalls(loadedData);
        CreateDiaphragms(loadedData);
        CreateSupports(loadedData);
        CreatePointLoads(loadedData);
        CreateGlobalAxes();
        CreateDiagramController();
        CreatePMPanel();

        BuildComboOptions();
        BuildFloorOptions();

        if (comboOptions.Length > 0)
        {
            ApplyCombo(0);
        }

        MarkGeneratedDontSave();
        RefreshVisibility();

        Debug.Log($"[StructureViewer] Estructura lista: {selectables.Count} elementos interactivos, {comboOptions.Length} combinaciones.");
    }

    private void BuildComboOptions()
    {
        if (loadedData.p1l4 == null || loadedData.p1l4.combinations == null || loadedData.p1l4.combinations.Length == 0)
        {
            comboOptions = new string[] { "G (sin combo)" };
            comboIndex = 0;
            return;
        }

        var names = new List<string>();
        foreach (ComboInfo c in loadedData.p1l4.combinations)
        {
            if (c != null && !string.IsNullOrEmpty(c.name))
            {
                names.Add(c.name);
            }
        }
        comboOptions = names.ToArray();
        comboIndex = Mathf.Clamp(comboIndex, 0, Mathf.Max(0, comboOptions.Length - 1));
    }

    private void ApplyCombo(int index)
    {
        if (comboOptions == null || comboOptions.Length == 0)
        {
            UnityData.ActiveCombo = null;
            return;
        }

        string name = comboOptions[Mathf.Clamp(index, 0, comboOptions.Length - 1)];
        if (name == "G (sin combo)")
        {
            name = "";
        }
        UnityData.ActiveCombo = name;
        comboIndex = index;

        if (diagramController != null && Application.isPlaying)
        {
            diagramController.Refresh();
        }

        if (pmPanel != null)
        {
            var picker = FindObjectOfType<ElementPicker>();
            if (picker != null && picker.Selected != null)
            {
                pmPanel.ShowPMForElement(picker.Selected);
            }
        }

        if (showUtilization)
        {
            ApplyUtilizationColors();
        }
    }

    private void MarkGeneratedDontSave()
    {
        for (int i = 0; i < transform.childCount; i++)
        {
            Transform child = transform.GetChild(i);
            if (child != null)
            {
                child.gameObject.hideFlags = HideFlags.DontSave;
            }
        }
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

            bool isColumn = element.type == "columna";
            float sectionWidth = GetSectionWidth(element, isColumn);
            float sectionHeight = GetSectionHeight(element, isColumn);

            GameObject member = GameObject.CreatePrimitive(PrimitiveType.Cube);
            member.name = $"Elemento_{element.id}_{element.type}_{GetSectionName(element)}";
            member.transform.SetParent(transform);
            member.transform.position = midpoint;
            member.transform.rotation = GetMemberRotation(direction, isColumn);
            member.transform.localScale = new Vector3(sectionWidth, direction.magnitude, sectionHeight);

            Renderer renderer = member.GetComponent<Renderer>();
            renderer.material = isColumn ? ColumnMaterial() : BeamMaterial();
            (isColumn ? columnObjects : beamObjects).Add(member);
            RegisterFloor(member, element.piso);

            ElementSelectable selectable = member.AddComponent<ElementSelectable>();
            selectable.data = element;
            selectable.startPoint = start;
            selectable.endPoint = end;
            selectable.nodeIId = element.nodeI;
            selectable.nodeJId = element.nodeJ;
            selectable.nodeISupport = FindSupportForNode(data, element.nodeI);
            selectable.nodeJSupport = FindSupportForNode(data, element.nodeJ);

            if (isColumn)
            {
                string secName = GetSectionName(element);
                selectable.pmSectionId = ResolvePMSection(secName);
            }

            selectables.Add(selectable);
        }
    }

    private SupportData FindSupportForNode(StructureData data, int nodeId)
    {
        if (data.supports == null)
        {
            return null;
        }
        foreach (SupportData s in data.supports)
        {
            if (s.node == nodeId)
            {
                return s;
            }
        }
        return null;
    }

    private string GetSectionName(ElementData element)
    {
        if (!string.IsNullOrEmpty(element.sectionId)) return element.sectionId;
        if (!string.IsNullOrEmpty(element.seccion)) return element.seccion;
        return element.type == "columna" ? "COL70/70" : "V60/80";
    }

    private float GetSectionWidth(ElementData element, bool isColumn)
    {
        if (element.width_m > 0.001f) return element.width_m;

        string sectionName = GetSectionName(element);
        if (sectionName == "V30/80") return 0.30f;
        if (sectionName == "V40/80") return 0.40f;
        if (sectionName == "V60/80") return 0.60f;
        if (sectionName == "V30/45") return 0.30f;
        return isColumn ? 0.70f : 0.60f;
    }

    private float GetSectionHeight(ElementData element, bool isColumn)
    {
        if (element.height_m > 0.001f) return element.height_m;

        string sectionName = GetSectionName(element);
        if (sectionName == "V30/45") return 0.45f;
        if (sectionName == "V30/80" || sectionName == "V40/80" || sectionName == "V60/80") return 0.80f;
        return isColumn ? 0.70f : 0.80f;
    }

    private Quaternion GetMemberRotation(Vector3 direction, bool isColumn)
    {
        Vector3 axis = direction.normalized;
        if (isColumn || Mathf.Abs(Vector3.Dot(axis, Vector3.up)) > 0.95f)
        {
            return Quaternion.FromToRotation(Vector3.up, axis);
        }

        Vector3 localX = Vector3.Cross(axis, Vector3.up).normalized;
        Vector3 localZ = Vector3.Cross(localX, axis).normalized;
        return Quaternion.LookRotation(localZ, axis);
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
            Vector3 baseMidpoint = (start + end) * 0.5f;
            Vector3 direction = end - start;
            float wallLength = Mathf.Max(direction.magnitude, wall.longitud, 0.01f);
            float wallHeight = EstimateWallHeight(start, end);
            Vector3 lengthAxis = direction.sqrMagnitude > 1e-8f ? direction.normalized : Vector3.forward;
            Vector3 midpoint = baseMidpoint + Vector3.up * (wallHeight * 0.5f);

            GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = $"Muro_{wall.id}";
            box.transform.SetParent(transform);
            box.transform.position = midpoint;
            box.transform.rotation = Quaternion.LookRotation(lengthAxis, Vector3.up);
            float thick = Mathf.Max(wall.grosor, 0.01f);
            box.transform.localScale = new Vector3(thick * wallScale, wallHeight, wallLength);
            box.GetComponent<Renderer>().material = WallMaterial();
            wallObjects.Add(box);
            RegisterFloor(box, wall.bottom);

            ElementSelectable selectable = box.AddComponent<ElementSelectable>();
            selectable.isWall = true;
            selectable.wallId = wall.id;
            selectable.wallThickness = wall.grosor;
            selectable.wallLength = wall.longitud;
            selectable.wallBottom = wall.bottom;
            selectable.wallTop = wall.top;
            selectable.wallSourceBuilding = wall.sourceBuilding;
            selectable.wallSourceId = wall.sourceId;
            selectable.startPoint = start;
            selectable.endPoint = end + Vector3.up * wallHeight;
            selectable.data = null;
            selectable.nodeIId = wall.nodeI;
            selectable.nodeJId = wall.nodeJ;
            selectable.nodeISupport = FindSupportForNode(data, wall.nodeI);
            selectable.nodeJSupport = FindSupportForNode(data, wall.nodeJ);

            string pmSec = ResolveWallPMSection(data, wall.id, wall.nodeI, wall.nodeJ);
            selectable.pmSectionId = pmSec;
            selectable.pmDemands = wall.demands;

            selectables.Add(selectable);
        }
    }

    private float EstimateWallHeight(Vector3 start, Vector3 end)
    {
        float baseY = Mathf.Min(start.y, end.y);
        float best = float.PositiveInfinity;
        foreach (Vector3 node in nodes.Values)
        {
            if (node.y <= baseY + 0.05f)
            {
                continue;
            }

            bool sameStartPlan = Mathf.Abs(node.x - start.x) < 0.05f && Mathf.Abs(node.z - start.z) < 0.05f;
            bool sameEndPlan = Mathf.Abs(node.x - end.x) < 0.05f && Mathf.Abs(node.z - end.z) < 0.05f;
            if (!sameStartPlan && !sameEndPlan)
            {
                continue;
            }

            best = Mathf.Min(best, node.y - baseY);
        }

        if (!float.IsInfinity(best))
        {
            return Mathf.Max(best, 0.5f);
        }

        return EstimateTypicalStoryHeight();
    }

    private float EstimateTypicalStoryHeight()
    {
        float best = float.PositiveInfinity;
        foreach (Vector3 a in nodes.Values)
        {
            foreach (Vector3 b in nodes.Values)
            {
                float diff = b.y - a.y;
                if (diff > 0.5f && diff < best)
                {
                    best = diff;
                }
            }
        }

        return float.IsInfinity(best) ? 4.0f : best;
    }

    private string ResolvePMSection(string sectionId)
    {
        if (UnityData.GetPMCurve(sectionId) != null)
        {
            return sectionId;
        }
        if (UnityData.GetPMCurve(sectionId + "_FIBER") != null)
        {
            return sectionId + "_FIBER";
        }
        return string.IsNullOrEmpty(sectionId) ? null : sectionId;
    }

    private string ResolveWallPMSection(StructureData data, int wallId, int nodeI, int nodeJ)
    {
        if (data.p1l4 != null && data.p1l4.wallRegistry != null)
        {
            foreach (WallRegistryEntry entry in data.p1l4.wallRegistry)
            {
                if (entry != null && (entry.index == wallId || (entry.nodeI == nodeI && entry.nodeJ == nodeJ)) && entry.hasCurve)
                {
                    return entry.pmSectionId;
                }
            }
        }
        return null;
    }

    private void CreateDiaphragms(StructureData data)
    {
        if (data.diaphragmList == null)
        {
            return;
        }

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

            InfoSelectable info = plane.AddComponent<InfoSelectable>();
            info.info = $"Diafragma rigido\n" +
                        $"Nivel: {dia.level}\n" +
                        $"Nodo maestro: {dia.maestro}\n" +
                        $"Esclavos: {(dia.slaves != null ? dia.slaves.Length : 0)}";

            diaphragmObjects.Add(plane);
            RegisterFloor(plane, dia.level);
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

            float area = dx * dy;
            float qG = data.q_G;
            float totalLoad = area * qG;
            InfoSelectable info = plane.AddComponent<InfoSelectable>();
            info.info = $"Losa / diafragma de area\n" +
                        $"ID: {slab.id}\n" +
                        $"Nivel: {slab.nivel}\n" +
                        $"Area: {area:0.###} m2\n" +
                        $"Dimensiones: {dx:0.###} x {dy:0.###} m\n" +
                        $"qG: {qG:0.###} kN/m2\n" +
                        $"Carga gravitacional estimada: {totalLoad:0.###} kN\n" +
                        $"Nota: visualizada como panel; no es shell OpenSees.";

            diaphragmObjects.Add(plane);
            RegisterFloor(plane, slab.nivel);
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
        if (diagramController != null)
        {
            if (Application.isPlaying)
            {
                Destroy(diagramController);
            }
            else
            {
                DestroyImmediate(diagramController);
            }
        }
        diagramController = gameObject.AddComponent<DiagramController>();
        diagramController.Initialize(selectables);
    }

    private void CreatePMPanel()
    {
        if (pmPanel != null)
        {
            if (Application.isPlaying)
            {
                Destroy(pmPanel);
            }
            else
            {
                DestroyImmediate(pmPanel);
            }
        }
        pmPanel = gameObject.AddComponent<PMPanel>();
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

    private void CreateLoadArrows(StructureData data)
    {
        if (data.slabs == null || data.slabs.Length == 0)
        {
            return;
        }

        float qG = data.q_G;
        int created = 0;
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

            float area = dx * dy;
            float load = area * qG;
            if (load < 1f)
            {
                continue;
            }

            Vector3 center = new Vector3(cx, slab.z, cy);
            float sign = -1f;
            Vector3 start = center + Vector3.up * sign * 0.9f;
            Vector3 end = center + Vector3.up * sign * 0.2f;
            Vector3 direction = end - start;

            GameObject arrow = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            arrow.name = $"Carga_Gravitacional_{slab.id}_{load:0}kN";
            arrow.transform.SetParent(transform);
            arrow.transform.position = (start + end) * 0.5f;
            arrow.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction.normalized);
            arrow.transform.localScale = new Vector3(0.045f, direction.magnitude * 0.5f, 0.045f);
            arrow.GetComponent<Renderer>().material = CreateMaterial(Color.red);
            loadObjects.Add(arrow);
            RegisterFloor(arrow, slab.nivel);

            GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            head.name = $"Punta_Carga_{slab.id}";
            head.transform.SetParent(transform);
            head.transform.position = end;
            head.transform.localScale = new Vector3(0.2f, 0.2f, 0.2f);
            head.GetComponent<Renderer>().material = CreateMaterial(Color.red);
            loadObjects.Add(head);
            RegisterFloor(head, slab.nivel);
            created++;
        }

        Debug.Log($"[StructureViewer] Flechas de carga gravitacional: {created} losas (qG={qG:0.###} kN/m2).");
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
    public void SetUtilizationVisible(bool visible)
    {
        showUtilization = visible;
        if (visible)
        {
            ApplyUtilizationColors();
        }
        else
        {
            RestoreUtilizationColors();
        }
        RefreshVisibility();
    }

    private void ApplyUtilizationColors()
    {
        foreach (ElementSelectable sel in selectables)
        {
            if (sel == null)
            {
                continue;
            }
            Renderer renderer = sel.GetComponent<Renderer>();
            if (renderer == null)
            {
                continue;
            }
            GameObject go = sel.gameObject;
            if (!originalUtilColors.ContainsKey(go))
            {
                originalUtilColors[go] = renderer.material.color;
            }
            renderer.material.color = UtilizationColor(sel.GetActiveUtilization());
        }
    }

    private void RestoreUtilizationColors()
    {
        foreach (ElementSelectable sel in selectables)
        {
            if (sel == null)
            {
                continue;
            }
            Renderer renderer = sel.GetComponent<Renderer>();
            GameObject go = sel.gameObject;
            if (renderer != null && originalUtilColors.ContainsKey(go))
            {
                renderer.material.color = originalUtilColors[go];
            }
        }
        originalUtilColors.Clear();
    }

    private Color UtilizationColor(float ratio)
    {
        if (ratio <= 0f) return new Color(0.75f, 0.75f, 0.75f);
        float clamped = Mathf.Clamp01(ratio);
        if (clamped <= 0.7f)
        {
            return Color.Lerp(new Color(0.2f, 0.9f, 0.3f), new Color(1f, 0.9f, 0.1f), clamped / 0.7f);
        }
        return Color.Lerp(new Color(1f, 0.9f, 0.1f), new Color(0.9f, 0.15f, 0.1f), (clamped - 0.7f) / 0.3f);
    }

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
            string label = GetSelectableLabel(sel);
            GameObject labelObject = new GameObject("Label_" + label.Replace(" ", "_"));
            labelObject.transform.SetParent(transform);
            Vector3 mid = (sel.startPoint + sel.endPoint) * 0.5f;
            labelObject.transform.position = mid + new Vector3(0, 0.3f, 0);

            TextMesh text = labelObject.AddComponent<TextMesh>();
            text.text = label;
            text.characterSize = 0.12f;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = Color.white;
            idLabelObjects.Add(labelObject);
            RegisterFloor(labelObject, GetSelectableFloor(sel));
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
            localAxis.name = "EjeLocal_" + GetSelectableLabel(sel).Replace(" ", "_");
            localAxis.transform.SetParent(transform);
            localAxis.transform.position = mid + dir * 0.75f;
            localAxis.transform.rotation = Quaternion.FromToRotation(Vector3.up, dir);
            localAxis.transform.localScale = new Vector3(0.02f, 0.75f, 0.02f);
            localAxis.GetComponent<Renderer>().material = CreateMaterial(Color.magenta);
            localAxisObjects.Add(localAxis);
            RegisterFloor(localAxis, GetSelectableFloor(sel));
        }
    }

    private void RefreshVisibility()
    {
        if (showNodeMarkers && nodeMarkerObjects.Count == 0)
        {
            CreateNodeMarkers();
        }
        if (showIds && idLabelObjects.Count == 0)
        {
            CreateIdLabels();
        }
        if (showLocalAxes && localAxisObjects.Count == 0)
        {
            CreateLocalAxes();
        }
        if (showLoads && loadObjects.Count == 0)
        {
            CreateLoadArrows(loadedData);
        }

        SetGroupVisible(columnObjects, showColumns);
        SetGroupVisible(beamObjects, showBeams);
        SetGroupVisible(wallObjects, showWalls);
        SetGroupVisible(supportObjects, showSupports);
        SetGroupVisible(diaphragmObjects, showDiaphragms);
        SetGroupVisible(nodeMarkerObjects, showNodeMarkers);
        SetGroupVisible(idLabelObjects, showIds);
        SetGroupVisible(localAxisObjects, showLocalAxes);
        SetGroupVisible(loadObjects, showLoads);
    }

    private void SetGroupVisible(List<GameObject> group, bool visible)
    {
        foreach (GameObject go in group)
        {
            if (go != null)
            {
                go.SetActive(visible && PassesFloorFilter(go));
            }
        }
    }

    private void RegisterFloor(GameObject go, string floor)
    {
        if (go == null)
        {
            return;
        }
        objectFloor[go] = NormalizeFloor(floor);
    }

    private bool PassesFloorFilter(GameObject go)
    {
        if (floorOptions == null || floorOptions.Length == 0 || floorIndex <= 0)
        {
            return true;
        }
        string selectedFloor = floorOptions[Mathf.Clamp(floorIndex, 0, floorOptions.Length - 1)];
        string goFloor;
        if (!objectFloor.TryGetValue(go, out goFloor))
        {
            return true;
        }
        return goFloor == selectedFloor;
    }

    private string NormalizeFloor(string floor)
    {
        return string.IsNullOrEmpty(floor) ? "Sin piso" : floor;
    }

    private void BuildFloorOptions()
    {
        var floors = new List<string>();
        floors.Add("Todos");

        foreach (string floor in objectFloor.Values)
        {
            if (!floors.Contains(floor))
            {
                floors.Add(floor);
            }
        }

        floorOptions = floors.ToArray();
        floorIndex = Mathf.Clamp(floorIndex, 0, Mathf.Max(0, floorOptions.Length - 1));
    }

    private void OnGUI()
    {
        DrawTopBar();
        DrawLeftPanel();
        DrawViewportHint();
        RefreshVisibility();
    }

    private void DrawTopBar()
    {
        float x = 12f;
        float y = 10f;
        float w = Screen.width - 24f;
        float h = 70f;
        GUI.Box(new Rect(x, y, w, h), "P1L4 Visualizador | TopBar");

        float cx = x + 12f;
        float cy = y + 25f;
        GUI.Label(new Rect(cx, cy, 54f, 22f), "Combo");
        if (comboOptions.Length > 0)
        {
            int index = GUI.Toolbar(new Rect(cx + 54f, cy, 245f, 22f), comboIndex, comboOptions);
            if (index != comboIndex)
            {
                comboIndex = index;
                ApplyCombo(comboIndex);
                statusMessage = "Combinacion activa: " + UnityData.GetComboLabel(UnityData.ActiveCombo);
            }
        }

        cx += 320f;
        GUI.Label(new Rect(cx, cy, 72f, 22f), "Resultado");
        int nextResult = GUI.Toolbar(new Rect(cx + 78f, cy, 380f, 22f), resultIndex, resultOptions);
        if (nextResult != resultIndex)
        {
            resultIndex = nextResult;
            if (diagramController != null)
            {
                diagramController.SetResultMode(resultOptions[resultIndex]);
            }
            statusMessage = "Resultado activo: " + resultOptions[resultIndex];
        }

        float bx = x + w - 245f;
        if (GUI.Button(new Rect(bx, cy, 55f, 22f), "ISO")) SetCameraPreset("ISO");
        if (GUI.Button(new Rect(bx + 60f, cy, 55f, 22f), "TOP")) SetCameraPreset("TOP");
        if (GUI.Button(new Rect(bx + 120f, cy, 55f, 22f), "FRONT")) SetCameraPreset("FRONT");
        if (GUI.Button(new Rect(bx + 180f, cy, 55f, 22f), "RIGHT")) SetCameraPreset("RIGHT");
    }

    private void DrawLeftPanel()
    {
        float x = 12f;
        float y = 90f;
        float w = Mathf.Min(340f, Screen.width * 0.34f);
        float h = Mathf.Min(Screen.height - 112f, 520f);
        GUI.Box(new Rect(x, y, w, h), "LeftPanel | Capas y filtro");

        float innerX = x + 12f;
        float innerY = y + 26f;
        float innerW = w - 24f;
        leftScroll = GUI.BeginScrollView(new Rect(x + 4f, innerY, w - 8f, h - 34f), leftScroll,
            new Rect(x + 4f, innerY, w - 24f, 520f));

        GUI.Label(new Rect(innerX, innerY, innerW, 20f), "Visibilidad");
        innerY += 22f;
        showColumns = GUI.Toggle(new Rect(innerX, innerY, 105f, 20f), showColumns, "Columnas");
        showBeams = GUI.Toggle(new Rect(innerX + 110f, innerY, 85f, 20f), showBeams, "Vigas");
        showWalls = GUI.Toggle(new Rect(innerX + 205f, innerY, 85f, 20f), showWalls, "Muros");
        innerY += 22f;
        showSupports = GUI.Toggle(new Rect(innerX, innerY, 105f, 20f), showSupports, "Apoyos");
        showDiaphragms = GUI.Toggle(new Rect(innerX + 110f, innerY, 85f, 20f), showDiaphragms, "Losas");
        showNodeMarkers = GUI.Toggle(new Rect(innerX + 205f, innerY, 85f, 20f), showNodeMarkers, "Nodos");
        innerY += 22f;
        showIds = GUI.Toggle(new Rect(innerX, innerY, 105f, 20f), showIds, "IDs");
        showLocalAxes = GUI.Toggle(new Rect(innerX + 110f, innerY, 120f, 20f), showLocalAxes, "Ejes locales");
        showLoads = GUI.Toggle(new Rect(innerX + 235f, innerY, 80f, 20f), showLoads, "Cargas");
        innerY += 34f;

        GUI.Label(new Rect(innerX, innerY, innerW, 20f), "Filtro por piso");
        innerY += 22f;
        int nextFloor = GUI.SelectionGrid(new Rect(innerX, innerY, innerW, Mathf.Ceil(floorOptions.Length / 2f) * 24f), floorIndex, floorOptions, 2);
        if (nextFloor != floorIndex)
        {
            floorIndex = nextFloor;
            statusMessage = "Filtro de piso: " + floorOptions[floorIndex];
        }
        innerY += Mathf.Ceil(floorOptions.Length / 2f) * 24f + 12f;

        if (GUI.Button(new Rect(innerX, innerY, 102f, 24f), "Mostrar todo"))
        {
            showColumns = showBeams = showWalls = showSupports = showDiaphragms = true;
            showNodeMarkers = showIds = showLocalAxes = showLoads = false;
            if (showUtilization)
            {
                showUtilization = false;
                RestoreUtilizationColors();
            }
            floorIndex = 0;
            statusMessage = "Vista restablecida.";
        }
        if (GUI.Button(new Rect(innerX + 110f, innerY, 102f, 24f), "Solo estructura"))
        {
            showColumns = showBeams = showWalls = true;
            showSupports = showDiaphragms = showNodeMarkers = showIds = showLocalAxes = showLoads = false;
            if (showUtilization)
            {
                showUtilization = false;
                RestoreUtilizationColors();
            }
            statusMessage = "Capas auxiliares ocultas.";
        }
        innerY += 34f;

        showTributarySummary = GUI.Toggle(new Rect(innerX, innerY, 180f, 20f), showTributarySummary, "Resumen tributario");
        innerY += 24f;
        if (showTributarySummary)
        {
            foreach (KeyValuePair<string, TributaryFloorData> kv in tributaryFloors)
            {
                TributaryFloorData td = kv.Value;
                GUI.Label(new Rect(innerX, innerY, innerW, 18f), $"{kv.Key}: A={td.area_total:0.##} m2 | carga={td.carga_total:0.##} kN");
                innerY += 18f;
            }
        }
        innerY += 6f;

        bool nextUtilization = GUI.Toggle(new Rect(innerX, innerY, 210f, 20f), showUtilization, "Colorear por utilizacion (C)");
        if (nextUtilization != showUtilization)
        {
            SetUtilizationVisible(nextUtilization);
            statusMessage = showUtilization ? "Colores por C = demanda/capacidad P-M." : "Colores por capa restaurados.";
        }
        innerY += 20f;
        if (showUtilization)
        {
            GUI.Label(new Rect(innerX, innerY, innerW, 20f), "verde: C<=0.7 | amarillo: C~1 | rojo: C>1");
            innerY += 20f;
        }

        GUI.EndScrollView();
    }

    private void DrawViewportHint()
    {
        float w = Mathf.Min(520f, Screen.width - 380f);
        if (w < 240f) return;
        GUI.Box(new Rect(370f, Screen.height - 46f, w, 32f), "MainViewport | " + statusMessage + " | Click izquierdo: seleccionar | Click derecho: orbitar | rueda: zoom");
    }

    private void SetCameraPreset(string preset)
    {
        Camera cam = Camera.main;
        if (cam == null) return;
        OrbitCamera orbit = cam.GetComponent<OrbitCamera>();
        if (orbit != null)
        {
            orbit.SetPreset(preset);
            statusMessage = "Vista de camara: " + preset;
        }
    }

    private string GetSelectableLabel(ElementSelectable sel)
    {
        if (sel == null) return "-";
        if (sel.isWall) return "Muro " + sel.wallId;
        if (sel.data == null) return sel.name;
        return sel.data.type + " " + (!string.IsNullOrEmpty(sel.data.elementTag) ? sel.data.elementTag : sel.data.id.ToString());
    }

    private string GetSelectableFloor(ElementSelectable sel)
    {
        if (sel == null) return "Sin piso";
        if (sel.isWall) return NormalizeFloor(sel.wallBottom);
        if (sel.data != null) return NormalizeFloor(sel.data.piso);
        return "Sin piso";
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
