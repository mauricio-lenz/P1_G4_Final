using System.Collections.Generic;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// Diagramas de esfuerzos (N, V, M) y deformada del combo activo.
///
/// - Escala COMUN a todo el modelo (no por barra): el tamano del diagrama
///   compara barras entre si. El factor se ajusta con DiagramScale.
/// - Diagrama relleno en el plano de flexion correcto, en ejes locales:
///     plano xz -> Vz y My (en vigas: flexion por gravedad, dibujado en vertical)
///     plano xy -> Vy y Mz (en vigas: flexion lateral, dibujado en horizontal)
///   El momento se dibuja del lado traccionado. Color por signo.
/// - Valores en el maximo de las barras mas solicitadas y en I/J del elemento
///   seleccionado; al pasar el mouse sobre un diagrama se lee x y el valor.
/// - Deformada curva (Hermite con los giros de OpenSees), coloreada por |u| y animable.
/// </summary>
[ExecuteAlways]
public class DiagramController : MonoBehaviour
{
    private enum DiagramMode { None, Axial, Shear, Moment, Deformed }

    public enum Plane { Auto, XZ, XY }
    public enum LabelMode { None, Maximos, Seleccionado }

    // ---- opciones (las usa la interfaz) ----
    public static float DiagramScale = 1f;          // 1 = el maximo del modelo mide TargetHeight
    public static Plane DiagramPlane = Plane.Auto;
    public static LabelMode Labels = LabelMode.Maximos;
    public static bool ShowBeams = true;
    public static bool ShowColumns = true;
    public static bool AnimateDeformed = true;
    public const float TargetHeight = 3.0f;          // m de dibujo para el maximo, con DiagramScale = 1
    private const int Samples = 24;
    private const int TopLabels = 10;

    public float deformedTargetPct = 0.05f;
    public float deformedMultiplier = 120f;

    private static readonly Color PosFill = new Color(0.20f, 0.62f, 0.98f, 0.42f);
    private static readonly Color NegFill = new Color(0.98f, 0.52f, 0.16f, 0.42f);
    private static readonly Color PosLine = new Color(0.45f, 0.78f, 1f, 1f);
    private static readonly Color NegLine = new Color(1f, 0.70f, 0.36f, 1f);

    private readonly List<ElementSelectable> structuralElements = new List<ElementSelectable>();
    private readonly List<GameObject> diagramObjects = new List<GameObject>();
    private DiagramMode currentMode = DiagramMode.None;
    private readonly Dictionary<string, float> deformedScaleByBuilding = new Dictionary<string, float>();

    // diagrama dibujado de cada elemento (para etiquetas y lectura con el mouse)
    private class ElemDiagram
    {
        public ElementSelectable el;
        public Plane plane;
        public string component;   // "N", "Vz", "My", ...
        public float length;
        public float[] t = new float[Samples + 1];
        public float[] v = new float[Samples + 1];
        public Vector3[] basePts = new Vector3[Samples + 1];
        public Vector3[] tipPts = new Vector3[Samples + 1];
        public int iMax;
    }
    private readonly List<ElemDiagram> drawn = new List<ElemDiagram>();
    private float drawnMax = 1f;
    private float drawnScale = 1f;   // m de dibujo por unidad de esfuerzo

    // deformada animada
    private class DeformedLine { public LineRenderer line; public Vector3[] basePts; public Vector3[] offPts; public Vector3[] buf; }
    private readonly List<DeformedLine> deformedLines = new List<DeformedLine>();
    private float deformedMaxMm;
    private float deformedScaleShown;

    // lectura con el mouse
    private ElemDiagram hoverDiagram;
    private int hoverIndex = -1;
    private Vector3 lastMouse;
    private int lastVisibleCount = -1;
    private float visibilityCheckAt;

    private Material fillMaterial;
    private Material lineMaterial;

    public void Initialize(List<ElementSelectable> selectables)
    {
        structuralElements.Clear();
        foreach (ElementSelectable e in selectables)
        {
            if (e.data != null) structuralElements.Add(e);
        }
        ShowDiagram(DiagramMode.None);
        Debug.Log($"[DiagramController] listo con {structuralElements.Count} elementos con datos (todos los edificios)");
    }

    private DiagramMode modeToRedraw = DiagramMode.None;

    public void SetResultMode(string modeName)
    {
        if (modeName == "Axial") ShowDiagram(DiagramMode.Axial);
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
        if (modeToRedraw != DiagramMode.None) ShowDiagram(modeToRedraw);
    }

    // ------------------------------------------------------------------
    private void Update()
    {
        if (!Application.isPlaying) return;

        if (PressedKey(KeyCode.Alpha0)) ShowDiagram(DiagramMode.None);
        if (PressedKey(KeyCode.Alpha1)) ShowDiagram(DiagramMode.Axial);
        if (PressedKey(KeyCode.Alpha2)) ShowDiagram(DiagramMode.Shear);
        if (PressedKey(KeyCode.Alpha3)) ShowDiagram(DiagramMode.Moment);
        if (PressedKey(KeyCode.Alpha4)) ShowDiagram(DiagramMode.Deformed);
        if (currentMode != DiagramMode.None)
        {
            if (PressedKey(KeyCode.Equals) || PressedKey(KeyCode.KeypadPlus)) ChangeScale(1.25f);
            if (PressedKey(KeyCode.Minus) || PressedKey(KeyCode.KeypadMinus)) ChangeScale(0.8f);
        }

        // el filtro de pisos/ocultar cambia que barras estan activas: redibujar
        if (currentMode != DiagramMode.None && Time.unscaledTime >= visibilityCheckAt)
        {
            visibilityCheckAt = Time.unscaledTime + 0.4f;
            int visible = 0;
            foreach (ElementSelectable e in structuralElements) if (e != null && e.gameObject.activeInHierarchy) visible++;
            if (lastVisibleCount >= 0 && visible != lastVisibleCount) Refresh();
            lastVisibleCount = visible;
        }

        if (currentMode == DiagramMode.Deformed) AnimateDeformedLines();
        else UpdateHover();
    }

    public void ChangeScale(float factor)
    {
        DiagramScale = Mathf.Clamp(DiagramScale * factor, 0.1f, 10f);
        Refresh();
    }

    private bool PressedKey(KeyCode key)
    {
#if ENABLE_INPUT_SYSTEM
        Keyboard k = Keyboard.current;
        if (k != null)
        {
            switch (key)
            {
                case KeyCode.Alpha0: return k.digit0Key.wasPressedThisFrame;
                case KeyCode.Alpha1: return k.digit1Key.wasPressedThisFrame;
                case KeyCode.Alpha2: return k.digit2Key.wasPressedThisFrame;
                case KeyCode.Alpha3: return k.digit3Key.wasPressedThisFrame;
                case KeyCode.Alpha4: return k.digit4Key.wasPressedThisFrame;
                case KeyCode.Equals: return k.equalsKey.wasPressedThisFrame;
                case KeyCode.Minus: return k.minusKey.wasPressedThisFrame;
                case KeyCode.KeypadPlus: return k.numpadPlusKey.wasPressedThisFrame;
                case KeyCode.KeypadMinus: return k.numpadMinusKey.wasPressedThisFrame;
            }
        }
#endif
        return Input.GetKeyDown(key);
    }

    // ---- modelo "alambre" mientras hay un diagrama ----
    private readonly Dictionary<Transform, Vector3> originalScales = new Dictionary<Transform, Vector3>();
    private readonly List<Renderer> hiddenRenderers = new List<Renderer>();
    private const float WireSection = 0.12f;

    private void SetLineModel(bool on)
    {
        if (on && originalScales.Count == 0)
        {
            foreach (ElementSelectable el in structuralElements)
            {
                if (el == null) continue;
                Transform t = el.transform;
                Vector3 orig = t.localScale;
                originalScales[t] = orig;
                t.localScale = new Vector3(Mathf.Min(orig.x, WireSection), orig.y, Mathf.Min(orig.z, WireSection));
                // el collider conserva el tamano original: seguir seleccionando con un clic comodo
                var box = el.GetComponent<BoxCollider>();
                if (box != null) box.size = new Vector3(orig.x / t.localScale.x, 1f, orig.z / t.localScale.z);
            }
            foreach (Transform child in transform)
            {
                string n = child.name;
                if (!(n.StartsWith("Losa_") || n.StartsWith("Diafragma_") || n.StartsWith("Etiqueta_Apoyo_"))) continue;
                foreach (Renderer r in child.GetComponentsInChildren<Renderer>())
                {
                    if (r.enabled) { r.enabled = false; hiddenRenderers.Add(r); }
                }
            }
        }
        else if (!on && originalScales.Count > 0)
        {
            foreach (var kv in originalScales)
            {
                if (kv.Key == null) continue;
                kv.Key.localScale = kv.Value;
                var box = kv.Key.GetComponent<BoxCollider>();
                if (box != null) box.size = Vector3.one;
            }
            originalScales.Clear();
            foreach (Renderer r in hiddenRenderers) if (r != null) r.enabled = true;
            hiddenRenderers.Clear();
        }
    }

    private void OnDisable()
    {
        SetLineModel(false);
    }

    private void ShowDiagram(DiagramMode mode)
    {
        currentMode = mode;
        modeToRedraw = mode;
        ClearDiagram();
        SetLineModel(mode != DiagramMode.None);
        if (mode == DiagramMode.None) return;
        if (mode == DiagramMode.Deformed)
        {
            deformedScaleByBuilding.Clear();
            CreateDeformedDiagram();
            return;
        }
        CreateForceDiagrams(mode);
    }

    // ------------------------------------------------------------------
    // Diagramas de esfuerzos
    // ------------------------------------------------------------------
    private bool Include(ElementSelectable el, DiagramMode mode)
    {
        if (el == null || el.data == null || !el.gameObject.activeInHierarchy) return false;
        if (UnityData.IsRemoved(el.data.id)) return false;
        string type = el.data.type;
        if (type == "arriostre") return mode == DiagramMode.Axial && ShowColumns;
        if (type == "viga") return ShowBeams;
        if (type == "columna") return ShowColumns;
        return true;
    }

    /// Ejes locales del elemento en coordenadas Unity (modelo (x,y,z) -> Unity (x,z,y)).
    private static void LocalAxesUnity(ElementData e, out Vector3 y, out Vector3 z)
    {
        UnityData.LocalAxes(e, out _, out Vector3 my, out Vector3 mz, out _);
        y = new Vector3(my.x, my.z, my.y);
        z = new Vector3(mz.x, mz.z, mz.y);
    }

    private void CreateForceDiagrams(DiagramMode mode)
    {
        drawn.Clear();
        float vmaxAll = 0f;
        foreach (ElementSelectable el in structuralElements)
        {
            if (!Include(el, mode)) continue;
            ElemDiagram d = Sample(el, mode);
            if (d == null) continue;
            drawn.Add(d);
            vmaxAll = Mathf.Max(vmaxAll, Mathf.Abs(d.v[d.iMax]));
        }
        drawnMax = Mathf.Max(vmaxAll, 1e-6f);
        drawnScale = TargetHeight * DiagramScale / drawnMax;

        var fillV = new List<Vector3>();
        var fillC = new List<Color>();
        var fillI = new List<int>();
        var lineV = new List<Vector3>();
        var lineC = new List<Color>();
        var lineI = new List<int>();

        foreach (ElemDiagram d in drawn)
        {
            LocalAxesUnity(d.el.data, out Vector3 ly, out Vector3 lz);
            Vector3 dir = OffsetDirection(d, ly, lz);
            float cs = ColorSign(d);
            for (int i = 0; i <= Samples; i++)
            {
                d.basePts[i] = Vector3.Lerp(d.el.startPoint, d.el.endPoint, d.t[i]);
                d.tipPts[i] = d.basePts[i] + dir * (d.v[i] * drawnScale);
            }
            for (int i = 0; i < Samples; i++)
            {
                float v0 = d.v[i], v1 = d.v[i + 1];
                if (v0 * v1 < 0f)
                {
                    // cruce por cero: dos trapecios con su color
                    float f = v0 / (v0 - v1);
                    Vector3 bz = Vector3.Lerp(d.basePts[i], d.basePts[i + 1], f);
                    AddQuad(fillV, fillC, fillI, d.basePts[i], d.tipPts[i], bz, bz, cs * v0 >= 0f ? PosFill : NegFill);
                    AddQuad(fillV, fillC, fillI, bz, bz, d.basePts[i + 1], d.tipPts[i + 1], cs * v1 >= 0f ? PosFill : NegFill);
                }
                else
                {
                    AddQuad(fillV, fillC, fillI, d.basePts[i], d.tipPts[i], d.basePts[i + 1], d.tipPts[i + 1],
                        cs * (v0 + v1) >= 0f ? PosFill : NegFill);
                }
                AddLine(lineV, lineC, lineI, d.tipPts[i], d.tipPts[i + 1], cs * (v0 + v1) >= 0f ? PosLine : NegLine);
            }
            // cierres en los extremos
            AddLine(lineV, lineC, lineI, d.basePts[0], d.tipPts[0], cs * d.v[0] >= 0f ? PosLine : NegLine);
            AddLine(lineV, lineC, lineI, d.basePts[Samples], d.tipPts[Samples], cs * d.v[Samples] >= 0f ? PosLine : NegLine);
        }

        CreateMeshObject("Diagrama_relleno_" + mode, fillV, fillC, fillI, MeshTopology.Triangles, FillMaterial());
        CreateMeshObject("Diagrama_contorno_" + mode, lineV, lineC, lineI, MeshTopology.Lines, LineMaterial());
        Debug.Log($"[DiagramController] {mode}: {drawn.Count} diagramas | max {drawnMax:0.0} {Unit(mode)} | escala {TargetHeight * DiagramScale:0.0} m");
    }

    private ElemDiagram Sample(ElementSelectable el, DiagramMode mode)
    {
        var d = new ElemDiagram { el = el, length = (el.endPoint - el.startPoint).magnitude };
        var rows = new float[Samples + 1][];
        float maxXZ = 0f, maxXY = 0f;
        for (int i = 0; i <= Samples; i++)
        {
            d.t[i] = i / (float)Samples;
            rows[i] = UnityData.InternalForcesAt(el.data, d.t[i]);
            if (rows[i] == null) return null;
            if (mode == DiagramMode.Moment) { maxXZ = Mathf.Max(maxXZ, Mathf.Abs(rows[i][4])); maxXY = Mathf.Max(maxXY, Mathf.Abs(rows[i][5])); }
            if (mode == DiagramMode.Shear) { maxXZ = Mathf.Max(maxXZ, Mathf.Abs(rows[i][2])); maxXY = Mathf.Max(maxXY, Mathf.Abs(rows[i][1])); }
        }
        Plane plane = DiagramPlane;
        if (plane == Plane.Auto) plane = mode == DiagramMode.Axial || maxXZ >= maxXY ? Plane.XZ : Plane.XY;
        d.plane = plane;
        int k = mode == DiagramMode.Axial ? 0
              : mode == DiagramMode.Shear ? (plane == Plane.XZ ? 2 : 1)
              : (plane == Plane.XZ ? 4 : 5);
        d.component = new[] { "N", "Vy", "Vz", "T", "My", "Mz" }[k];
        for (int i = 0; i <= Samples; i++)
        {
            d.v[i] = rows[i][k];
            if (Mathf.Abs(d.v[i]) > Mathf.Abs(d.v[d.iMax])) d.iMax = i;
        }
        return d;
    }

    /// Direccion del dibujo: My se dibuja del lado traccionado (+z local cuando My > 0),
    /// Mz del lado traccionado (−y local cuando Mz > 0); N y V en el mismo plano.
    private Vector3 OffsetDirection(ElemDiagram d, Vector3 ly, Vector3 lz)
    {
        if (currentMode == DiagramMode.Moment) return d.plane == Plane.XZ ? lz : -ly;
        if (currentMode == DiagramMode.Shear) return d.plane == Plane.XZ ? lz : ly;
        return lz;
    }

    /// Color por convencion de diseno: en el plano xz el momento con traccion abajo
    /// (My local negativo) es M+ (azul); en el resto, el signo local.
    private float ColorSign(ElemDiagram d)
    {
        return currentMode == DiagramMode.Moment && d.plane == Plane.XZ ? -1f : 1f;
    }

    private static void AddQuad(List<Vector3> v, List<Color> c, List<int> idx, Vector3 b0, Vector3 t0, Vector3 b1, Vector3 t1, Color color)
    {
        int s = v.Count;
        v.Add(b0); v.Add(t0); v.Add(b1); v.Add(t1);
        c.Add(color); c.Add(color); c.Add(color); c.Add(color);
        idx.Add(s); idx.Add(s + 1); idx.Add(s + 2);
        idx.Add(s + 2); idx.Add(s + 1); idx.Add(s + 3);
    }

    private static void AddLine(List<Vector3> v, List<Color> c, List<int> idx, Vector3 a, Vector3 b, Color color)
    {
        int s = v.Count;
        v.Add(a); v.Add(b); c.Add(color); c.Add(color);
        idx.Add(s); idx.Add(s + 1);
    }

    private void CreateMeshObject(string name, List<Vector3> verts, List<Color> colors, List<int> indices, MeshTopology topology, Material mat)
    {
        if (verts.Count == 0) return;
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        go.hideFlags = HideFlags.DontSave;
        var mesh = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
        mesh.SetVertices(verts);
        mesh.SetColors(colors);
        mesh.SetIndices(indices, topology, 0);
        mesh.RecalculateBounds();
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var mr = go.AddComponent<MeshRenderer>();
        mr.sharedMaterial = mat;
        mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        mr.receiveShadows = false;
        diagramObjects.Add(go);
    }

    private Material FillMaterial()
    {
        if (fillMaterial == null)
        {
            fillMaterial = new Material(Shader.Find("Sprites/Default")) { renderQueue = 3100 };
        }
        return fillMaterial;
    }

    private Material LineMaterial()
    {
        if (lineMaterial == null)
        {
            lineMaterial = new Material(Shader.Find("Sprites/Default")) { renderQueue = 3110 };
        }
        return lineMaterial;
    }

    // ------------------------------------------------------------------
    // Deformada: curva de Hermite con los giros nodales, color por |u|
    // ------------------------------------------------------------------
    private void CreateDeformedDiagram()
    {
        deformedLines.Clear();
        string combo = UnityData.ActiveCombo;
        if (string.IsNullOrEmpty(combo) || UnityData.DisplacementsByCombo == null)
        {
            Debug.LogWarning("[DiagramController] No hay desplazamientos para el combo activo.");
            return;
        }
        bool compare = UnityData.CompareDeformedActive;

        // |u| maximo de lo que se dibuja (para el color)
        deformedMaxMm = 0f;
        foreach (ElementSelectable el in structuralElements)
        {
            if (el.data == null || !el.gameObject.activeInHierarchy) continue;
            deformedMaxMm = Mathf.Max(deformedMaxMm,
                UnityData.GetNodeDisplacement(combo, el.data.nodeI).magnitude * 1000f,
                UnityData.GetNodeDisplacement(combo, el.data.nodeJ).magnitude * 1000f);
        }
        deformedMaxMm = Mathf.Max(deformedMaxMm, 1e-6f);

        int created = 0;
        foreach (ElementSelectable el in structuralElements)
        {
            if (el.data == null || !el.gameObject.activeInHierarchy) continue;
            bool removed = UnityData.IsRemoved(el.data.id);
            if (removed && !compare) continue;
            string building = string.IsNullOrEmpty(el.data.sourceBuilding) ? "?" : el.data.sourceBuilding;
            float scale = GetDeformedScale(building, combo);
            if (scale <= 0f) scale = deformedMultiplier;
            deformedScaleShown = scale;

            if (compare)
            {
                Vector3 oI = UnityData.GetOriginalNodeDisplacement(combo, el.data.nodeI);
                Vector3 oJ = UnityData.GetOriginalNodeDisplacement(combo, el.data.nodeJ);
                AddDeformedLine(el, new[] { el.startPoint, el.endPoint }, new[] { oI * scale, oJ * scale },
                    new Color(1f, 0.6f, 0.15f, 0.85f), new Color(1f, 0.6f, 0.15f, 0.85f), 0.08f, "Deformada_Original_E" + el.data.id);
            }
            if (removed) continue;

            BuildDeformedShape(el.data, combo, scale, el.startPoint, el.endPoint, out Vector3[] basePts, out Vector3[] offPts);
            float uI = UnityData.GetNodeDisplacement(combo, el.data.nodeI).magnitude * 1000f;
            float uJ = UnityData.GetNodeDisplacement(combo, el.data.nodeJ).magnitude * 1000f;
            AddDeformedLine(el, basePts, offPts, Heat(uI / deformedMaxMm), Heat(uJ / deformedMaxMm), 0.2f, "Deformada_E" + el.data.id);
            created++;
        }
        Debug.Log($"[DiagramController] Deformada {combo}: {created} elementos, |u| max {deformedMaxMm:0.00} mm, escala x{deformedScaleShown:0}");
    }

    /// Puntos de la elastica: ejes locales, axial lineal, flexion con Hermite (giros de OpenSees).
    private static void BuildDeformedShape(ElementData e, string combo, float scale, Vector3 a, Vector3 b,
        out Vector3[] basePts, out Vector3[] offPts)
    {
        const int n = 12;
        basePts = new Vector3[n + 1];
        offPts = new Vector3[n + 1];
        DisplacementRecord dI = UnityData.GetDisplacementRecord(combo, e.nodeI);
        DisplacementRecord dJ = UnityData.GetDisplacementRecord(combo, e.nodeJ);
        Vector3 uI = dI != null ? new Vector3(dI.ux, dI.uy, dI.uz) : Vector3.zero;   // modelo
        Vector3 uJ = dJ != null ? new Vector3(dJ.ux, dJ.uy, dJ.uz) : Vector3.zero;
        Vector3 rI = dI != null ? new Vector3(dI.rx, dI.ry, dI.rz) : Vector3.zero;
        Vector3 rJ = dJ != null ? new Vector3(dJ.rx, dJ.ry, dJ.rz) : Vector3.zero;
        bool hasRot = rI.sqrMagnitude > 0f || rJ.sqrMagnitude > 0f;   // combos sinteticos no traen giros

        UnityData.LocalAxes(e, out Vector3 lx, out Vector3 ly, out Vector3 lz, out float L);
        float vI = Vector3.Dot(uI, ly), vJ = Vector3.Dot(uJ, ly);
        float wI = Vector3.Dot(uI, lz), wJ = Vector3.Dot(uJ, lz);
        float tzI = Vector3.Dot(rI, lz), tzJ = Vector3.Dot(rJ, lz);   // dv/dx = theta_z
        float tyI = -Vector3.Dot(rI, ly), tyJ = -Vector3.Dot(rJ, ly); // dw/dx = −theta_y

        for (int i = 0; i <= n; i++)
        {
            float s = i / (float)n;
            basePts[i] = Vector3.Lerp(a, b, s);
            Vector3 u = Vector3.Lerp(uI, uJ, s);   // lineal (axial y sin giros)
            if (hasRot && L > 1e-6f)
            {
                float h1 = 1f - 3f * s * s + 2f * s * s * s, h2 = L * (s - 2f * s * s + s * s * s);
                float h3 = 3f * s * s - 2f * s * s * s, h4 = L * (-s * s + s * s * s);
                float axial = Mathf.Lerp(Vector3.Dot(uI, lx), Vector3.Dot(uJ, lx), s);
                float v = h1 * vI + h2 * tzI + h3 * vJ + h4 * tzJ;
                float w = h1 * wI + h2 * tyI + h3 * wJ + h4 * tyJ;
                u = axial * lx + v * ly + w * lz;
            }
            offPts[i] = new Vector3(u.x, u.z, u.y) * scale;   // a Unity
        }
    }

    private void AddDeformedLine(ElementSelectable el, Vector3[] basePts, Vector3[] offPts, Color c0, Color c1, float width, string name)
    {
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        go.hideFlags = HideFlags.DontSave;
        var line = go.AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.positionCount = basePts.Length;
        line.widthMultiplier = width;
        line.numCapVertices = 2;
        line.sharedMaterial = LineMaterial();
        line.startColor = c0;
        line.endColor = c1;
        line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        var dl = new DeformedLine { line = line, basePts = basePts, offPts = offPts, buf = new Vector3[basePts.Length] };
        SetDeformedPositions(dl, AnimateDeformed && Application.isPlaying ? AnimationFactor() : 1f);
        deformedLines.Add(dl);
        diagramObjects.Add(go);
    }

    private static float AnimationFactor()
    {
        return 0.5f - 0.5f * Mathf.Cos(Time.unscaledTime * Mathf.PI * 2f / 2.4f);
    }

    private void AnimateDeformedLines()
    {
        float f = AnimateDeformed ? AnimationFactor() : 1f;
        foreach (DeformedLine dl in deformedLines) SetDeformedPositions(dl, f);
    }

    private static void SetDeformedPositions(DeformedLine dl, float f)
    {
        for (int i = 0; i < dl.basePts.Length; i++) dl.buf[i] = dl.basePts[i] + dl.offPts[i] * f;
        dl.line.SetPositions(dl.buf);
    }

    /// Azul (0) -> cian -> amarillo -> rojo (1).
    private static Color Heat(float x)
    {
        x = Mathf.Clamp01(x);
        if (x < 0.33f) return Color.Lerp(new Color(0.25f, 0.45f, 1f), new Color(0.2f, 0.9f, 0.95f), x / 0.33f);
        if (x < 0.66f) return Color.Lerp(new Color(0.2f, 0.9f, 0.95f), new Color(1f, 0.9f, 0.25f), (x - 0.33f) / 0.33f);
        return Color.Lerp(new Color(1f, 0.9f, 0.25f), new Color(1f, 0.25f, 0.2f), (x - 0.66f) / 0.34f);
    }

    private float GetDeformedScale(string building, string combo)
    {
        if (UnityData.DeformedScaleOverride > 0f) return UnityData.DeformedScaleOverride;
        if (deformedScaleByBuilding.TryGetValue(building, out float cached)) return cached;
        bool compare = UnityData.CompareDeformedActive;
        Bounds bounds = new Bounds();
        bool first = true;
        float maxDisp = 0f;
        foreach (ElementSelectable e in structuralElements)
        {
            if (e.data == null) continue;
            string eb = string.IsNullOrEmpty(e.data.sourceBuilding) ? "?" : e.data.sourceBuilding;
            if (eb != building) continue;
            if (first) { bounds = new Bounds(e.startPoint, Vector3.zero); first = false; }
            bounds.Encapsulate(e.startPoint);
            bounds.Encapsulate(e.endPoint);
            maxDisp = Mathf.Max(maxDisp, UnityData.GetNodeDisplacement(combo, e.data.nodeI).magnitude,
                UnityData.GetNodeDisplacement(combo, e.data.nodeJ).magnitude);
            if (compare)
            {
                maxDisp = Mathf.Max(maxDisp, UnityData.GetOriginalNodeDisplacement(combo, e.data.nodeI).magnitude,
                    UnityData.GetOriginalNodeDisplacement(combo, e.data.nodeJ).magnitude);
            }
        }
        float scale = maxDisp >= 1e-9f ? (bounds.size.y + 1f) * deformedTargetPct * DiagramScale / maxDisp : 0f;
        deformedScaleByBuilding[building] = scale;
        return scale;
    }

    // ------------------------------------------------------------------
    // Lectura con el mouse
    // ------------------------------------------------------------------
    private void UpdateHover()
    {
        Camera cam = Camera.main;
        if (cam == null || drawn.Count == 0) { hoverDiagram = null; return; }
        Vector3 mouse = Input.mousePosition;
        if ((mouse - lastMouse).sqrMagnitude < 1f) return;
        lastMouse = mouse;
        hoverDiagram = null;
        hoverIndex = -1;
        if (UiTheme.IsOverUI(mouse, FindAnyObjectByType<ElementPicker>()?.Selected != null)) return;

        float best = 14f * 14f * UiTheme.Scale * UiTheme.Scale;
        foreach (ElemDiagram d in drawn)
        {
            for (int i = 0; i <= Samples; i++)
            {
                Vector3 sp = cam.WorldToScreenPoint(d.tipPts[i]);
                if (sp.z <= 0f) continue;
                float dist = ((Vector2)sp - (Vector2)mouse).sqrMagnitude;
                if (dist < best) { best = dist; hoverDiagram = d; hoverIndex = i; }
            }
        }
    }

    // ------------------------------------------------------------------
    // Interfaz: barra de opciones, leyenda, etiquetas, tabla del seleccionado
    // ------------------------------------------------------------------
    private GUIStyle tagStyle;

    private void OnGUI()
    {
        if (currentMode == DiagramMode.None) return;
        UiTheme.ApplyScale();
        DrawLabels();
        DrawOptionsBar();
        DrawSelectedValueTable();
    }

    private string ModeTitle()
    {
        switch (currentMode)
        {
            case DiagramMode.Axial: return "AXIAL N";
            case DiagramMode.Shear: return "CORTE";
            case DiagramMode.Moment: return "MOMENTO";
            case DiagramMode.Deformed: return "DEFORMADA";
        }
        return "";
    }

    private static string Unit(DiagramMode mode)
    {
        return mode == DiagramMode.Moment ? "kN·m" : "kN";
    }

    private void DrawOptionsBar()
    {
        float w = 560f, h = 58f;
        Rect r = UiTheme.CenterTop(w, h);
        UiTheme.GUIBox(r);
        float x = r.x + 10f, y = r.y + 6f;
        string combo = UnityData.GetComboLabel(UnityData.ActiveCombo);

        if (currentMode == DiagramMode.Deformed)
        {
            GUI.Label(new Rect(x, y, r.width - 20f, 18f),
                $"DEFORMADA · {combo} · |u| max {deformedMaxMm:0.00} mm · escala x{deformedScaleShown:0}", UiTheme.TitleSm);
            y += 24f;
            DrawHeatLegend(new Rect(x, y + 4f, 150f, 12f));
            GUI.Label(new Rect(x + 156f, y, 70f, 20f), $"{deformedMaxMm:0.0} mm", UiTheme.DimLabel);
            bool anim = GUI.Toggle(new Rect(x + 236f, y, 90f, 22f), AnimateDeformed, " Animar");
            if (anim != AnimateDeformed) { AnimateDeformed = anim; AnimateDeformedLines(); }
            DrawScaleButtons(r.xMax - 132f, y);
            return;
        }

        string plane = DiagramPlane == Plane.Auto ? "plano dominante" : DiagramPlane == Plane.XZ ? "plano local xz" : "plano local xy";
        GUI.Label(new Rect(x, y, r.width - 20f, 18f),
            $"{ModeTitle()} · {combo} · max {drawnMax:0.0} {Unit(currentMode)} · {plane}", UiTheme.TitleSm);
        y += 24f;

        // leyenda de signo
        GUI.color = PosLine; GUI.DrawTexture(new Rect(x, y + 5f, 12f, 12f), UiTheme.White()); GUI.color = Color.white;
        GUI.Label(new Rect(x + 15f, y + 2f, 36f, 20f), currentMode == DiagramMode.Axial ? "trac." : "+", UiTheme.DimLabel);
        GUI.color = NegLine; GUI.DrawTexture(new Rect(x + 52f, y + 5f, 12f, 12f), UiTheme.White()); GUI.color = Color.white;
        GUI.Label(new Rect(x + 67f, y + 2f, 40f, 20f), currentMode == DiagramMode.Axial ? "comp." : "−", UiTheme.DimLabel);
        if (currentMode == DiagramMode.Moment)
        {
            GUI.Label(new Rect(x, r.yMax + 2f, r.width, 18f),
                "M dibujado del lado traccionado · vigas: + = traccion abajo (My local < 0)", UiTheme.DimLabel);
        }

        float bx = x + 110f;
        string[] planes = { "Auto", "xz (My·Vz)", "xy (Mz·Vy)" };
        if (currentMode != DiagramMode.Axial)
        {
            int p = GUI.Toolbar(new Rect(bx, y, 200f, 22f), (int)DiagramPlane, planes);
            if (p != (int)DiagramPlane) { DiagramPlane = (Plane)p; Refresh(); }
        }
        bx += 206f;
        bool beams = GUI.Toggle(new Rect(bx, y + 1f, 62f, 22f), ShowBeams, " Vigas");
        bool cols = GUI.Toggle(new Rect(bx + 62f, y + 1f, 82f, 22f), ShowColumns, " Columnas");
        if (beams != ShowBeams || cols != ShowColumns) { ShowBeams = beams; ShowColumns = cols; Refresh(); }
        DrawScaleButtons(r.xMax - 132f, y);

        // etiquetas: ciclo Max / Sel / No con un boton pequeno
        string[] lab = { "Etiq: no", "Etiq: max", "Etiq: sel" };
        if (GUI.Button(new Rect(r.xMax - 132f, r.y + 6f, 122f, 18f), lab[(int)Labels]))
        {
            Labels = (LabelMode)(((int)Labels + 1) % 3);
        }
    }

    private void DrawScaleButtons(float x, float y)
    {
        if (GUI.Button(new Rect(x, y, 30f, 22f), "−")) ChangeScale(0.8f);
        GUI.Label(new Rect(x + 34f, y + 2f, 54f, 20f), $"x{DiagramScale:0.##}", UiTheme.Label);
        if (GUI.Button(new Rect(x + 92f, y, 30f, 22f), "+")) ChangeScale(1.25f);
    }

    private void DrawHeatLegend(Rect r)
    {
        const int steps = 20;
        for (int i = 0; i < steps; i++)
        {
            GUI.color = Heat(i / (float)(steps - 1));
            GUI.DrawTexture(new Rect(r.x + r.width * i / steps, r.y, r.width / steps + 1f, r.height), UiTheme.White());
        }
        GUI.color = Color.white;
    }

    private void DrawLabels()
    {
        Camera cam = Camera.main;
        if (cam == null || currentMode == DiagramMode.Deformed) return;
        if (tagStyle == null)
        {
            tagStyle = new GUIStyle(UiTheme.Label) { fontSize = 11, alignment = TextAnchor.MiddleCenter, wordWrap = false };
            tagStyle.normal.background = UiTheme.MakeTex(new Color(0.03f, 0.05f, 0.09f, 0.82f));
            tagStyle.padding = new RectOffset(4, 4, 1, 1);
        }

        ElementSelectable selected = FindAnyObjectByType<ElementPicker>()?.Selected;
        if (Labels == LabelMode.Maximos && drawn.Count > 0)
        {
            var top = new List<ElemDiagram>(drawn);
            top.Sort((p, q) => Mathf.Abs(q.v[q.iMax]).CompareTo(Mathf.Abs(p.v[p.iMax])));
            for (int i = 0; i < Mathf.Min(TopLabels, top.Count); i++)
            {
                ElemDiagram d = top[i];
                DrawTag(cam, d.tipPts[d.iMax], $"{d.el.data.elementTag}  {d.v[d.iMax]:0.0}");
            }
        }
        if (Labels != LabelMode.None && selected != null)
        {
            ElemDiagram d = drawn.Find(x => x.el == selected);
            if (d != null)
            {
                DrawTag(cam, d.tipPts[0], $"I {d.v[0]:0.0}");
                DrawTag(cam, d.tipPts[Samples], $"J {d.v[Samples]:0.0}");
                if (d.iMax != 0 && d.iMax != Samples) DrawTag(cam, d.tipPts[d.iMax], $"max {d.v[d.iMax]:0.0}");
            }
        }
        if (hoverDiagram != null && hoverIndex >= 0)
        {
            ElemDiagram d = hoverDiagram;
            string text = $"{d.el.data.elementTag} · x = {d.t[hoverIndex] * d.length:0.00} m · {d.component} = {d.v[hoverIndex]:0.0} {Unit(currentMode)}";
            Vector3 sp = cam.WorldToScreenPoint(d.tipPts[hoverIndex]);
            Vector2 g = new Vector2(sp.x, Screen.height - sp.y) / UiTheme.Scale;
            Vector2 size = tagStyle.CalcSize(new GUIContent(text));
            GUI.color = new Color(1f, 1f, 1f, 0.95f);
            GUI.DrawTexture(new Rect(g.x - 3f, g.y - 3f, 6f, 6f), UiTheme.White());
            GUI.color = Color.white;
            GUI.Label(new Rect(g.x + 10f, g.y - size.y - 6f, size.x + 4f, size.y + 2f), text, tagStyle);
        }
    }

    private void DrawTag(Camera cam, Vector3 world, string text)
    {
        Vector3 sp = cam.WorldToScreenPoint(world);
        if (sp.z <= 0f) return;
        Vector2 g = new Vector2(sp.x, Screen.height - sp.y) / UiTheme.Scale;
        if (g.x < 0f || g.y < 0f || g.x > UiTheme.ScreenW || g.y > UiTheme.ScreenH) return;
        Vector2 size = tagStyle.CalcSize(new GUIContent(text));
        GUI.Label(new Rect(g.x - size.x / 2f, g.y - size.y - 2f, size.x + 4f, size.y + 2f), text, tagStyle);
    }

    private void DrawSelectedValueTable()
    {
        if (currentMode == DiagramMode.Deformed) return;
        ElementSelectable selected = FindAnyObjectByType<ElementPicker>()?.Selected;
        if (selected == null) return;
        if (selected.data == null && selected.isWall) { DrawSelectedWallValueTable(selected); return; }
        if (selected.data == null) return;

        ElemDiagram d = drawn.Find(x => x.el == selected) ?? Sample(selected, currentMode);
        if (d == null) return;
        float[] rI = UnityData.InternalForcesAt(selected.data, 0f) ?? new float[6];
        float[] rJ = UnityData.InternalForcesAt(selected.data, 1f) ?? new float[6];
        string tag = !string.IsNullOrEmpty(selected.data.elementTag) ? selected.data.elementTag : selected.data.id.ToString();
        string unit = Unit(currentMode);
        float xMax = d.t[d.iMax] * d.length;
        string body = $"{d.component}:  I = {d.v[0]:0.0}  |  centro = {d.v[Samples / 2]:0.0}  |  J = {d.v[Samples]:0.0} {unit}\n" +
                      $"max |{d.component}| = {d.v[d.iMax]:0.0} {unit} en x = {xMax:0.00} m de I (L = {d.length:0.00} m)\n";
        if (currentMode == DiagramMode.Moment)
            body += $"My I/J = {rI[4]:0.0} / {rJ[4]:0.0}   Mz I/J = {rI[5]:0.0} / {rJ[5]:0.0} kN·m";
        else if (currentMode == DiagramMode.Shear)
            body += $"Vy I/J = {rI[1]:0.0} / {rJ[1]:0.0}   Vz I/J = {rI[2]:0.0} / {rJ[2]:0.0} kN";
        else
            body += $"N I/J = {rI[0]:0.0} / {rJ[0]:0.0} kN   T I/J = {rI[3]:0.0} / {rJ[3]:0.0} kN·m";

        Rect bar = UiTheme.CenterTop(560f, 58f);
        Rect r = new Rect(bar.x, bar.yMax + 6f, bar.width, 82f);
        UiTheme.GUIBox(r, $"{ModeTitle()} · {tag} ({selected.data.type} {selected.data.sectionId})");
        GUI.Label(new Rect(r.x + 12f, r.y + 26f, r.width - 24f, r.height - 30f), body, UiTheme.Label);
    }

    private void DrawSelectedWallValueTable(ElementSelectable selected)
    {
        DemandRecord demand = selected.GetActiveWallDemand();
        if (demand == null) return;
        string body;
        if (currentMode == DiagramMode.Axial) body = $"N demanda = {demand.P_kN:0.0} kN";
        else if (currentMode == DiagramMode.Shear) body = $"V en el plano = {demand.V_kN:0.0} kN (fuera del plano ~ 0, muro equivalente)";
        else body = $"M demanda P-M = {demand.M_kN_m:0.0} kN·m";
        Rect bar = UiTheme.CenterTop(560f, 58f);
        Rect r = new Rect(bar.x, bar.yMax + 6f, bar.width, 62f);
        UiTheme.GUIBox(r, $"{ModeTitle()} · Muro {selected.wallId} · {UnityData.GetComboLabel(demand.combo)}");
        GUI.Label(new Rect(r.x + 12f, r.y + 26f, r.width - 24f, r.height - 30f), body, UiTheme.Label);
    }

    private void ClearDiagram()
    {
        foreach (GameObject go in diagramObjects)
        {
            if (go == null) continue;
            var mf = go.GetComponent<MeshFilter>();
            if (mf != null && mf.sharedMesh != null)
            {
                if (Application.isPlaying) Destroy(mf.sharedMesh); else DestroyImmediate(mf.sharedMesh);
            }
            if (Application.isPlaying) Destroy(go); else DestroyImmediate(go);
        }
        diagramObjects.Clear();
        deformedLines.Clear();
        drawn.Clear();
        hoverDiagram = null;
    }
}
