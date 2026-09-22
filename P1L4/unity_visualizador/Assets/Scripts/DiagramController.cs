using System.Collections.Generic;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

[ExecuteAlways]
public class DiagramController : MonoBehaviour
{
    private enum DiagramMode
    {
        None,
        Axial,
        Shear,
        Moment,
        Deformed
    }

    public float diagramScale = 1.3f;
    public float axialMultiplier = 0.9f;
    public float shearMultiplier = 1.0f;
    public float momentMultiplier = 1.2f;
    public float diagramBaseOffset = 0.06f;
    public float deformedMultiplier = 120f;
    public float deformedTargetPct = 0.06f;

    private readonly List<ElementSelectable> elements = new List<ElementSelectable>();
    private readonly List<ElementSelectable> structuralElements = new List<ElementSelectable>();
    private readonly List<GameObject> diagramObjects = new List<GameObject>();
    private DiagramMode currentMode = DiagramMode.None;
    private readonly Dictionary<string, float> deformedScaleByBuilding = new Dictionary<string, float>();
    private Dictionary<string, float> currentMaxByBuilding = new Dictionary<string, float>();
    private GUIStyle tableBoxStyle;
    private GUIStyle tableTextStyle;
    private GUIStyle tableTitleStyle;

    public void Initialize(List<ElementSelectable> selectables)
    {
        elements.Clear();
        elements.AddRange(selectables);
        structuralElements.Clear();
        foreach (ElementSelectable e in elements)
        {
            if (e.data != null)
            {
                structuralElements.Add(e);
            }
        }

        ShowDiagram(DiagramMode.None);
        Debug.Log($"[DiagramController] listo con {structuralElements.Count} elementos con datos (todos los edificios)");
    }

    private DiagramMode modeToRedraw = DiagramMode.None;

    public void SetResultMode(string modeName)
    {
        if (modeName == "None" || modeName == "Exploration") ShowDiagram(DiagramMode.None);
        else if (modeName == "Axial") ShowDiagram(DiagramMode.Axial);
        else if (modeName == "Corte") ShowDiagram(DiagramMode.Shear);
        else if (modeName == "Momento") ShowDiagram(DiagramMode.Moment);
        else if (modeName == "Deformada") ShowDiagram(DiagramMode.Deformed);
        else ShowDiagram(DiagramMode.None);
    }

    public string CurrentResultName()
    {
        if (currentMode == DiagramMode.Shear) return "Corte";
        if (currentMode == DiagramMode.Moment) return "Momento";
        if (currentMode == DiagramMode.Deformed) return "Deformada";
        return currentMode.ToString();
    }

    public void Refresh()
    {
        if (modeToRedraw != DiagramMode.None)
        {
            ShowDiagram(modeToRedraw);
        }
    }

    private void Update()
    {
        if (!Application.isPlaying) return;

        if (PressedKey(KeyCode.Alpha0)) ShowDiagram(DiagramMode.None);
        if (PressedKey(KeyCode.Alpha1)) ShowDiagram(DiagramMode.Axial);
        if (PressedKey(KeyCode.Alpha2)) ShowDiagram(DiagramMode.Shear);
        if (PressedKey(KeyCode.Alpha3)) ShowDiagram(DiagramMode.Moment);
        if (PressedKey(KeyCode.Alpha5)) ShowDiagram(DiagramMode.Deformed);
    }

    private bool PressedKey(KeyCode key)
    {
#if ENABLE_INPUT_SYSTEM
        Keyboard keyboard = Keyboard.current;
        if (keyboard != null)
        {
            if (key == KeyCode.Alpha0) return keyboard.digit0Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha1) return keyboard.digit1Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha2) return keyboard.digit2Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha3) return keyboard.digit3Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha5) return keyboard.digit5Key.wasPressedThisFrame;
        }
#endif
        return Input.GetKeyDown(key);
    }

    private void ShowDiagram(DiagramMode mode)
    {
        currentMode = mode;
        modeToRedraw = mode;
        ClearDiagram();

        if (mode == DiagramMode.None)
        {
            return;
        }

        if (mode == DiagramMode.Deformed)
        {
            deformedScaleByBuilding.Clear();
            CreateDeformedDiagram();
            Debug.Log("[DiagramController] modo Deformada activado (escala por edificio)");
            return;
        }

        currentMaxByBuilding.Clear();
        currentMaxByBuilding = GetMaxValueByBuilding(mode);
        int created = 0;

        foreach (ElementSelectable element in structuralElements)
        {
            if ((mode == DiagramMode.Moment || mode == DiagramMode.Shear) && element.data.type != "viga")
            {
                continue;
            }

            CreateElementDiagram(element, mode);
            created++;
        }

        Debug.Log($"[DiagramController] modo {mode}: {created} diagramas, max por edificio {FormatMaxByBuilding()}");
    }

    private string FormatMaxByBuilding()
    {
        var parts = new List<string>();
        foreach (KeyValuePair<string, float> kv in currentMaxByBuilding)
        {
            parts.Add($"{kv.Key}={kv.Value:0.###}");
        }
        return parts.Count == 0 ? "-" : string.Join(", ", parts);
    }

    private void CreateDeformedDiagram()
    {
        string combo = UnityData.ActiveCombo;
        if (string.IsNullOrEmpty(combo) || UnityData.DisplacementsByCombo == null)
        {
            Debug.LogWarning("[DiagramController] No hay desplazamientos para el combo activo.");
            return;
        }

        int created = 0;
        var scales = new List<string>();
        foreach (ElementSelectable element in structuralElements)
        {
            string building = string.IsNullOrEmpty(element.data.sourceBuilding) ? "?" : element.data.sourceBuilding;
            float scale = GetDeformedScale(building, combo);
            if (scale <= 0f)
            {
                scale = deformedMultiplier;
            }

            Vector3 dI = UnityData.GetNodeDisplacement(combo, element.data.nodeI);
            Vector3 dJ = UnityData.GetNodeDisplacement(combo, element.data.nodeJ);

            Vector3 p0 = element.startPoint + dI * scale;
            Vector3 p1 = element.endPoint + dJ * scale;

            CreateLine(element.startPoint, element.endPoint, new Color(0.5f, 0.5f, 0.55f, 0.6f), 0.04f,
                $"Deformada_Ref_E{element.data.id}");

            CreateLine(p0, p1, new Color(0.35f, 1f, 0.4f), 0.16f,
                $"Deformada_E{element.data.id}");

            created++;
        }

        foreach (var kv in deformedScaleByBuilding)
        {
            scales.Add($"{kv.Key}={kv.Value:0.#}");
        }
        Debug.Log($"[DiagramController] Deformada combo={combo}: {created} elementos, escala por edificio {string.Join(", ", scales)} ({deformedTargetPct * 100:0.#}% de la altura por edificio)");
    }

    private void CreateLine(Vector3 a, Vector3 b, Color color, float width, string name)
    {
        GameObject lineObject = new GameObject(name);
        lineObject.transform.SetParent(transform);
        lineObject.hideFlags = HideFlags.DontSave;
        LineRenderer line = lineObject.AddComponent<LineRenderer>();
        line.positionCount = 2;
        line.SetPosition(0, a);
        line.SetPosition(1, b);
        line.startWidth = width;
        line.endWidth = width;
        line.useWorldSpace = true;
        line.material = CreateMaterial(color);
        diagramObjects.Add(lineObject);
    }

    private float GetDeformedScale(string building, string combo)
    {
        if (deformedScaleByBuilding.TryGetValue(building, out float cached))
        {
            return cached;
        }

        Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
        float maxDisp = 0f;
        bool first = true;

        foreach (ElementSelectable e in structuralElements)
        {
            if (e.data == null) continue;
            string eb = string.IsNullOrEmpty(e.data.sourceBuilding) ? "?" : e.data.sourceBuilding;
            if (eb != building) continue;

            Vector3 a = e.startPoint;
            Vector3 b = e.endPoint;
            if (first)
            {
                bounds = new Bounds(a, Vector3.zero);
                bounds.Encapsulate(b);
                first = false;
            }
            else
            {
                bounds.Encapsulate(a);
                bounds.Encapsulate(b);
            }

            Vector3 dI = UnityData.GetNodeDisplacement(combo, e.data.nodeI);
            Vector3 dJ = UnityData.GetNodeDisplacement(combo, e.data.nodeJ);
            maxDisp = Mathf.Max(maxDisp, dI.magnitude, dJ.magnitude);
        }

        float scale = 0f;
        if (maxDisp >= 1e-9f)
        {
            float height = bounds.size.y + 1f;
            scale = (height * deformedTargetPct) / maxDisp;
        }

        deformedScaleByBuilding[building] = scale;
        return scale;
    }

    private Dictionary<string, float> GetMaxValueByBuilding(DiagramMode mode)
    {
        var result = new Dictionary<string, float>();

        foreach (ElementSelectable element in structuralElements)
        {
            if (element.data == null) continue;
            if ((mode == DiagramMode.Moment || mode == DiagramMode.Shear) && element.data.type != "viga")
            {
                continue;
            }

            string building = string.IsNullOrEmpty(element.data.sourceBuilding) ? "?" : element.data.sourceBuilding;
            if (!result.ContainsKey(building))
            {
                result[building] = 0.001f;
            }

            float buildingMax = result[building];
            int segments = 20;
            for (int i = 0; i <= segments; i++)
            {
                float t = i / (float)segments;
                float length = (element.endPoint - element.startPoint).magnitude;
                buildingMax = Mathf.Max(buildingMax, Mathf.Abs(GetValue(element, mode, t, length)));
            }
            result[building] = buildingMax;
        }

        return result;
    }

    private void CreateElementDiagram(ElementSelectable element, DiagramMode mode)
    {
        int segments = 12;
        Vector3[] points = new Vector3[segments + 1];
        Vector3 axis = element.endPoint - element.startPoint;
        Vector3 offsetDirection = GetOffsetDirection(axis, mode);
        float length = axis.magnitude;

        for (int i = 0; i <= segments; i++)
        {
            float t = i / (float)segments;
            Vector3 basePoint = Vector3.Lerp(element.startPoint, element.endPoint, t);
            float value = GetValue(element, mode, t, length);
            float maxValue = MaxForElement(element);
            points[i] = basePoint + offsetDirection * (diagramBaseOffset + value / maxValue * ScaleFor(mode));
        }

        GameObject lineObject = new GameObject($"Diagrama_{mode}_E{element.data.id}");
        lineObject.transform.SetParent(transform);
        lineObject.hideFlags = HideFlags.DontSave;
        LineRenderer line = lineObject.AddComponent<LineRenderer>();
        line.positionCount = points.Length;
        line.SetPositions(points);
        line.startWidth = 0.08f;
        line.endWidth = 0.08f;
        line.useWorldSpace = true;
        line.material = CreateMaterial(GetColor(mode));
        diagramObjects.Add(lineObject);

        CreateLabel(points[0], GetValue(element, mode, 0f, length), UnitFor(mode), lineObject.transform);
        CreateLabel(points[segments / 2], GetValue(element, mode, 0.5f, length), UnitFor(mode), lineObject.transform);
        CreateLabel(points[segments], GetValue(element, mode, 1f, length), UnitFor(mode), lineObject.transform);
    }

    private float MaxForElement(ElementSelectable element)
    {
        if (element == null || element.data == null) return 1f;
        string building = string.IsNullOrEmpty(element.data.sourceBuilding) ? "?" : element.data.sourceBuilding;
        return currentMaxByBuilding.TryGetValue(building, out float v) ? v : 1f;
    }

    private float GetValue(ElementSelectable element, DiagramMode mode, float t, float length)
    {
        ElementData data = element.data;
        if (data == null)
        {
            return 0f;
        }

        if (mode == DiagramMode.Axial)
        {
            return GetForceGradient(data, t, 0, 6);
        }

        if (mode == DiagramMode.Shear)
        {
            float vy = GetForceGradient(data, t, 1, 7);
            float vz = GetForceGradient(data, t, 2, 8);
            float sign = Mathf.Abs(vy) >= Mathf.Abs(vz) ? Mathf.Sign(vy) : Mathf.Sign(vz);
            return sign * Mathf.Sqrt(vy * vy + vz * vz);
        }

        float my = GetForceGradient(data, t, 4, 10);
        float mz = GetForceGradient(data, t, 5, 11);
        if (data.type == "viga" && Mathf.Abs(data.uniformLoad) > 1e-9f)
        {
            mz += Mathf.Abs(data.uniformLoad) * length * length * t * (1f - t) / 2f;
        }
        float momentSign = Mathf.Abs(my) >= Mathf.Abs(mz) ? Mathf.Sign(my) : Mathf.Sign(mz);
        return momentSign * Mathf.Sqrt(my * my + mz * mz);
    }

    private float GetForceGradient(ElementData data, float t, int iIndex, int jIndex)
    {
        if (!string.IsNullOrEmpty(UnityData.ActiveCombo) && UnityData.ElementForcesByCombo != null)
        {
            float[] f = UnityData.GetElementForces(UnityData.ActiveCombo, data.id);
            if (f != null && f.Length >= 12 && iIndex < 12 && jIndex < 12)
            {
                return Mathf.Lerp(f[iIndex], f[jIndex], t);
            }
        }

        if (iIndex == 0)
        {
            return Mathf.Lerp(data.axialI, data.axialJ, t);
        }
        if (iIndex == 1)
        {
            return Mathf.Lerp(data.shearI, data.shearJ, t);
        }
        return Mathf.Lerp(data.momentI, data.momentJ, t);
    }

    private float ScaleFor(DiagramMode mode)
    {
        if (mode == DiagramMode.Axial) return diagramScale * axialMultiplier;
        if (mode == DiagramMode.Shear) return diagramScale * shearMultiplier;
        return diagramScale * momentMultiplier;
    }

    private Vector3 GetOffsetDirection(Vector3 axis, DiagramMode mode)
    {
        if (mode == DiagramMode.Moment && Mathf.Abs(axis.normalized.y) < 0.2f)
        {
            return Vector3.up;
        }

        Vector3 direction = Vector3.Cross(axis.normalized, Vector3.forward).normalized;
        if (direction.sqrMagnitude < 0.01f)
        {
            direction = Vector3.right;
        }

        return direction;
    }

    private Color GetColor(DiagramMode mode)
    {
        if (mode == DiagramMode.Axial) return Color.red;
        if (mode == DiagramMode.Shear) return new Color(1f, 0.55f, 0f);
        if (mode == DiagramMode.Moment) return Color.magenta;
        if (mode == DiagramMode.Deformed) return new Color(0.3f, 1f, 0.4f);
        return Color.green;
    }

    private string UnitFor(DiagramMode mode)
    {
        if (mode == DiagramMode.Moment) return " kN*m";
        return " kN";
    }

    private void CreateLabel(Vector3 position, float value, string unit, Transform parent)
    {
        GameObject labelObject = new GameObject("ValorDiagrama");
        labelObject.transform.SetParent(parent);
        labelObject.hideFlags = HideFlags.DontSave;
        labelObject.transform.position = position + Vector3.up * 0.18f;

        TextMesh text = labelObject.AddComponent<TextMesh>();
        text.text = value.ToString("0.0") + unit;
        text.characterSize = 0.2f;
        text.anchor = TextAnchor.MiddleCenter;
        text.color = Color.white;
    }

    private Material CreateMaterial(Color color)
    {
        Shader shader = Shader.Find("Custom/AlwaysOnTopLine");
        if (shader == null) shader = Shader.Find("Unlit/Color");
        if (shader == null) shader = Shader.Find("Sprites/Default");
        if (shader == null) shader = Shader.Find("Standard");

        Material material = new Material(shader);
        material.color = color;
        material.renderQueue = shader.name == "Custom/AlwaysOnTopLine" ? 5000 : 4000;
        return material;
    }

    private void ClearDiagram()
    {
        foreach (GameObject diagramObject in diagramObjects)
        {
            if (Application.isPlaying)
            {
                Destroy(diagramObject);
            }
            else
            {
                DestroyImmediate(diagramObject);
            }
        }

        diagramObjects.Clear();
    }

    private void OnGUI()
    {
        DrawSelectedValueTable();
    }

    private void DrawSelectedValueTable()
    {
        if (currentMode == DiagramMode.None || currentMode == DiagramMode.Deformed)
        {
            return;
        }

        ElementPicker picker = FindObjectOfType<ElementPicker>();
        if (picker == null || picker.Selected == null)
        {
            return;
        }

        EnsureTableStyles();
        ElementSelectable selected = picker.Selected;
        if (selected.data == null && selected.isWall)
        {
            DrawSelectedWallValueTable(selected);
            return;
        }
        if (selected.data == null)
        {
            return;
        }

        ElementData data = selected.data;
        float length = (selected.endPoint - selected.startPoint).magnitude;
        float vi = GetValue(selected, currentMode, 0f, length);
        float vm = GetValue(selected, currentMode, 0.5f, length);
        float vj = GetValue(selected, currentMode, 1f, length);

        float vmax = vi;
        int segments = 24;
        for (int i = 0; i <= segments; i++)
        {
            float t = i / (float)segments;
            float v = GetValue(selected, currentMode, t, length);
            if (Mathf.Abs(v) > Mathf.Abs(vmax))
            {
                vmax = v;
            }
        }

        float nI, vyI, vzI, tI, myI, mzI;
        float nJ, vyJ, vzJ, tJ, myJ, mzJ;
        GetForcesAt(selected, 0f, length, out nI, out vyI, out vzI, out tI, out myI, out mzI);
        GetForcesAt(selected, 1f, length, out nJ, out vyJ, out vzJ, out tJ, out myJ, out mzJ);

        string tag = !string.IsNullOrEmpty(data.elementTag) ? data.elementTag : data.id.ToString();
        string unit = UnitFor(currentMode).Trim();
        string title = $"Valores {currentMode} - {tag}";
        string body = $"Combo: {UnityData.GetComboLabel(UnityData.ActiveCombo)}\n" +
                      $"I = {vi:0.##} {unit} | centro = {vm:0.##} {unit} | J = {vj:0.##} {unit}\n" +
                      $"Max abs = {vmax:0.##} {unit}\n";

        if (currentMode == DiagramMode.Moment)
        {
            body += $"My I/J = {myI:0.##} / {myJ:0.##} kN*m\n" +
                    $"Mz I/J = {mzI:0.##} / {mzJ:0.##} kN*m";
        }
        else if (currentMode == DiagramMode.Shear)
        {
            body += $"Vy I/J = {vyI:0.##} / {vyJ:0.##} kN\n" +
                    $"Vz I/J = {vzI:0.##} / {vzJ:0.##} kN";
        }
        else
        {
            body += $"N I/J = {nI:0.##} / {nJ:0.##} kN\n" +
                    $"T I/J = {tI:0.##} / {tJ:0.##} kN*m";
        }

        float w = Mathf.Min(380f, Screen.width * 0.34f);
        float h = 132f;
        float x = Mathf.Max(16f, (Screen.width - w) * 0.5f);
        float y = Screen.height - h - 18f;
        GUI.Box(new Rect(x, y, w, h), GUIContent.none, tableBoxStyle);
        GUI.Label(new Rect(x + 12f, y + 8f, w - 24f, 22f), title, tableTitleStyle);
        GUI.Label(new Rect(x + 12f, y + 32f, w - 24f, h - 40f), body, tableTextStyle);
    }

    private void DrawSelectedWallValueTable(ElementSelectable selected)
    {
        DemandRecord demand = selected.GetActiveWallDemand();
        if (demand == null)
        {
            return;
        }

        float value = 0f;
        string unit = "kN";
        string detail = "";
        if (currentMode == DiagramMode.Axial)
        {
            value = demand.P_kN;
            detail = $"N demanda = {demand.P_kN:0.##} kN";
        }
        else if (currentMode == DiagramMode.Shear)
        {
            value = demand.V_kN;
            unit = "kN";
            detail = $"Vz (corte en plano) demanda = {demand.V_kN:0.##} kN; Vy fuera de plano ~ 0 (muro equivalente).";
        }
        else if (currentMode == DiagramMode.Moment)
        {
            value = demand.M_kN_m;
            unit = "kN*m";
            detail = $"My/Mz demanda P-M = {demand.M_kN_m:0.##} kN*m";
        }

        string body = $"Combo: {UnityData.GetComboLabel(demand.combo)}\n" +
                      $"I = {value:0.##} {unit} | centro = {value:0.##} {unit} | J = {value:0.##} {unit}\n" +
                      $"Max abs = {value:0.##} {unit}\n" +
                      detail;

        float w = Mathf.Min(380f, Screen.width * 0.34f);
        float h = 118f;
        float x = Mathf.Max(16f, (Screen.width - w) * 0.5f);
        float y = Screen.height - h - 18f;
        GUI.Box(new Rect(x, y, w, h), GUIContent.none, tableBoxStyle);
        GUI.Label(new Rect(x + 12f, y + 8f, w - 24f, 22f), $"Valores {currentMode} - Muro {selected.wallId}", tableTitleStyle);
        GUI.Label(new Rect(x + 12f, y + 32f, w - 24f, h - 40f), body, tableTextStyle);
    }

    private void GetForcesAt(ElementSelectable element, float t, float length,
        out float n, out float vy, out float vz, out float torsion, out float my, out float mz)
    {
        ElementData data = element.data;
        n = GetForceGradient(data, t, 0, 6);
        vy = GetForceGradient(data, t, 1, 7);
        vz = GetForceGradient(data, t, 2, 8);
        torsion = GetForceGradient(data, t, 3, 9);
        my = GetForceGradient(data, t, 4, 10);
        mz = GetForceGradient(data, t, 5, 11);
        if (data.type == "viga" && Mathf.Abs(data.uniformLoad) > 1e-9f)
        {
            mz += Mathf.Abs(data.uniformLoad) * length * length * t * (1f - t) / 2f;
        }
    }

    private void EnsureTableStyles()
    {
        if (tableBoxStyle != null) return;
        tableBoxStyle = new GUIStyle(GUI.skin.box);
        tableBoxStyle.normal.background = MakeTex(new Color(0.03f, 0.03f, 0.04f, 0.88f));
        tableTextStyle = new GUIStyle(GUI.skin.label);
        tableTextStyle.fontSize = 13;
        tableTextStyle.normal.textColor = Color.white;
        tableTextStyle.wordWrap = true;
        tableTitleStyle = new GUIStyle(tableTextStyle);
        tableTitleStyle.fontStyle = FontStyle.Bold;
        tableTitleStyle.fontSize = 14;
    }

    private Texture2D MakeTex(Color color)
    {
        Texture2D tex = new Texture2D(1, 1);
        tex.SetPixel(0, 0, color);
        tex.Apply();
        return tex;
    }
}
