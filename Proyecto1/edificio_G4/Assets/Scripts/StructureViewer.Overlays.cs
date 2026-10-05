using System.Collections.Generic;
using UnityEngine;

/// Capas de la demo: ejes de grilla de los planos, diafragmas rigidos (nodo maestro,
/// centro de masa, peso y fuerza sismica por piso) y cargas del caso activo
/// (G y Q repartidas sobre cada viga, EX y EY en el nodo maestro), escaladas con
/// los lambda de la combinacion o de la superposicion.
public partial class StructureViewer
{
    private readonly List<GameObject> gridObjects = new List<GameObject>();
    private readonly List<GameObject> diaphragmMarkObjects = new List<GameObject>();
    private bool showGrid = false;
    private bool showDiaphragmMarks = false;
    private string loadOverlayKey;
    private Material overlayFillMaterial, overlayLineMaterial;

    public bool ShowGridLayer { get => showGrid; set => showGrid = value; }
    public bool ShowDiaphragmsLayer { get => showDiaphragmMarks; set => showDiaphragmMarks = value; }
    /// Resumen de la capa de cargas para la interfaz (caso, w maxima, fuerzas sismicas).
    public string LoadOverlaySummary { get; private set; } = "";

    private static readonly Color GridColor = new Color(0.95f, 0.75f, 0.25f, 0.9f);
    private static readonly Color GridSecondaryColor = new Color(0.75f, 0.65f, 0.45f, 0.5f);
    private static readonly Color DiaphragmColor = new Color(0.30f, 0.85f, 1f, 0.95f);
    private static readonly Color GravityColor = new Color(1f, 0.45f, 0.20f, 1f);
    private static readonly Color ExColor = new Color(0.25f, 0.90f, 0.35f, 1f);
    private static readonly Color EyColor = new Color(0.75f, 0.45f, 1f, 1f);

    private void ClearOverlayState()
    {
        gridObjects.Clear();
        diaphragmMarkObjects.Clear();
        loadOverlayKey = null;
    }

    private Material OverlayFill()
    {
        if (overlayFillMaterial == null) overlayFillMaterial = new Material(Shader.Find("Sprites/Default")) { renderQueue = 3090 };
        return overlayFillMaterial;
    }

    private Material OverlayLine()
    {
        if (overlayLineMaterial == null) overlayLineMaterial = new Material(Shader.Find("Sprites/Default")) { renderQueue = 3095 };
        return overlayLineMaterial;
    }

    /// Cota de la grilla de ejes: sobre la cubierta, para que se lea en la vista TOP.
    private float GridLevel()
    {
        float z = float.MinValue;
        foreach (Vector3 p in nodes.Values) z = Mathf.Max(z, p.y);
        return z == float.MinValue ? 0f : z + 0.6f;
    }

    private GameObject MeshObject(string name, List<Vector3> v, List<Color> c, List<int> i, MeshTopology topology, Material mat)
    {
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        var mesh = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
        mesh.SetVertices(v);
        mesh.SetColors(c);
        mesh.SetIndices(i, topology, 0);
        mesh.RecalculateBounds();
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var mr = go.AddComponent<MeshRenderer>();
        mr.sharedMaterial = mat;
        mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        mr.receiveShadows = false;
        return go;
    }

    private GameObject Label(string name, string text, Vector3 pos, Color color, float size, bool flat)
    {
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        go.transform.position = pos;
        if (flat) go.transform.rotation = Quaternion.Euler(90f, 0f, 0f);   // legible en planta (vista TOP)
        else go.AddComponent<FaceCamera>();
        var tm = go.AddComponent<TextMesh>();
        tm.text = text;
        tm.characterSize = size;
        tm.fontSize = 48;
        tm.anchor = TextAnchor.MiddleCenter;
        tm.color = color;
        return go;
    }

    // ---------------------------------------------------------------- ejes
    private void CreateGridAxes(StructureData data)
    {
        if (data.ejesGrilla == null || data.ejesGrilla.Length == 0) return;
        float z = GridLevel();
        var v = new List<Vector3>(); var c = new List<Color>(); var idx = new List<int>();
        foreach (EjeGrillaData e in data.ejesGrilla)
        {
            Color col = e.secundario ? GridSecondaryColor : GridColor;
            // direccion "y": eje paralelo a Y global (letras, coord = x); "x": paralelo a X (numeros, coord = y)
            Vector3 a = e.direccion == "y" ? new Vector3(e.coord, z, e.desde) : new Vector3(e.desde, z, e.coord);
            Vector3 b = e.direccion == "y" ? new Vector3(e.coord, z, e.hasta) : new Vector3(e.hasta, z, e.coord);
            // linea de trazos de 1 m
            Vector3 d = b - a;
            float len = d.magnitude;
            int n = Mathf.Max(1, Mathf.FloorToInt(len / 1.0f));
            for (int k = 0; k < n; k += 2)
            {
                v.Add(a + d * (k / (float)n)); v.Add(a + d * (Mathf.Min(k + 1, n) / (float)n));
                c.Add(col); c.Add(col); idx.Add(v.Count - 2); idx.Add(v.Count - 1);
            }
            // burbujas en ambos extremos: circulo + nombre
            float r = e.secundario ? 0.45f : 0.7f;
            foreach (Vector3 end in new[] { a - d.normalized * r, b + d.normalized * r })
            {
                int seg = 24;
                for (int k = 0; k < seg; k++)
                {
                    float t0 = k * Mathf.PI * 2f / seg, t1 = (k + 1) * Mathf.PI * 2f / seg;
                    v.Add(end + new Vector3(Mathf.Cos(t0), 0f, Mathf.Sin(t0)) * r);
                    v.Add(end + new Vector3(Mathf.Cos(t1), 0f, Mathf.Sin(t1)) * r);
                    c.Add(col); c.Add(col); idx.Add(v.Count - 2); idx.Add(v.Count - 1);
                }
                gridObjects.Add(Label($"Eje_{e.edificio}_{e.nombre}", e.nombre, end + Vector3.up * 0.02f, col, e.secundario ? 0.18f : 0.3f, true));
            }
        }
        gridObjects.Add(MeshObject("Ejes_de_grilla", v, c, idx, MeshTopology.Lines, OverlayLine()));
    }

    // ---------------------------------------------------------- diafragmas
    private void CreateDiaphragmMarks(StructureData data)
    {
        if (data.diafragmasSismo == null) return;
        foreach (DiafragmaData d in data.diafragmasSismo)
        {
            var v = new List<Vector3>(); var c = new List<Color>(); var idx = new List<int>();
            float y = d.z + 0.03f;
            Vector3[] corners = { new Vector3(d.x0, y, d.y0), new Vector3(d.x1, y, d.y0), new Vector3(d.x1, y, d.y1), new Vector3(d.x0, y, d.y1) };
            for (int k = 0; k < 4; k++)
            {
                v.Add(corners[k]); v.Add(corners[(k + 1) % 4]);
                c.Add(DiaphragmColor); c.Add(DiaphragmColor); idx.Add(v.Count - 2); idx.Add(v.Count - 1);
            }
            Vector3 cm = new Vector3(d.cm_x, y, d.cm_y);
            float s = 1.0f;
            foreach (Vector3 dir in new[] { Vector3.right, Vector3.forward })
            {
                v.Add(cm - dir * s); v.Add(cm + dir * s);
                c.Add(Color.magenta); c.Add(Color.magenta); idx.Add(v.Count - 2); idx.Add(v.Count - 1);
            }
            string tag = d.edificio.Replace("edificio_", "E");
            GameObject outline = MeshObject($"Diafragma_{tag}_{d.piso}", v, c, idx, MeshTopology.Lines, OverlayLine());
            diaphragmMarkObjects.Add(outline);
            RegisterFloor(outline, d.piso);

            if (nodes.TryGetValue(d.maestro, out Vector3 master))
            {
                GameObject m = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                m.name = $"Maestro_{tag}_{d.piso}_N{d.maestro}";
                m.transform.SetParent(transform);
                m.transform.position = master;
                m.transform.localScale = Vector3.one * 0.65f;
                m.GetComponent<Renderer>().material = CreateMaterial(new Color(1f, 0.55f, 0.1f));
                var info = m.AddComponent<InfoSelectable>();
                info.info = $"Diafragma rigido {tag} · {d.piso}\nNodo maestro: N{d.maestro} ({d.esclavos} esclavos)\n" +
                            $"Centro de masa: ({d.cm_x:0.00}, {d.cm_y:0.00}) m\nW sismico: {d.W_kN:0} kN · Ak {d.A_k:0.000}\n" +
                            $"F EX = {d.F_EX_kN:0} kN · F EY = {d.F_EY_kN:0} kN";
                diaphragmMarkObjects.Add(m);
                RegisterFloor(m, d.piso);
            }
            GameObject label = Label($"Etiqueta_Diafragma_{tag}_{d.piso}",
                $"Diafragma {tag} · {d.piso}\nmaestro N{d.maestro} · W {d.W_kN:0} kN", cm + Vector3.up * 1.4f, DiaphragmColor, 0.22f, false);
            diaphragmMarkObjects.Add(label);
            RegisterFloor(label, d.piso);
        }
    }

    // ------------------------------------------------------------- cargas
    private float[] ActiveLambdas()
    {
        string combo = UnityData.ActiveCombo;
        if (combo == UnityData.SuperpositionComboName) return UnityData.SuperpositionLambdas;
        switch (combo)
        {
            case "G": return new[] { 1f, 0f, 0f, 0f };
            case "Q": return new[] { 0f, 1f, 0f, 0f };
            case "EX": return new[] { 0f, 0f, 1f, 0f };
            case "EY": return new[] { 0f, 0f, 0f, 1f };
        }
        ComboInfo info = UnityData.GetComboInfo(combo);
        return info != null ? new[] { info.G, info.Q, info.EX, info.EY } : new[] { 1f, 0f, 0f, 0f };
    }

    /// Reconstruye la capa de cargas si cambio el caso activo o los lambda de la superposicion.
    private void EnsureLoadOverlay()
    {
        float[] l = ActiveLambdas();
        string key = $"{UnityData.ActiveCombo}|{l[0]:0.###}|{l[1]:0.###}|{l[2]:0.###}|{l[3]:0.###}";
        if (key == loadOverlayKey && loadObjects.Count > 0) return;
        foreach (GameObject go in loadObjects) if (go != null) { objectFloor.Remove(go); if (Application.isPlaying) Destroy(go); else DestroyImmediate(go); }
        loadObjects.Clear();
        loadOverlayKey = key;
        if (loadedData == null) return;
        CreateGravityLoads(loadedData, l[0], l[1], out float wMax);
        CreateSeismicArrows(loadedData, l[2], l[3], out float fx, out float fy);
        string caso = string.IsNullOrEmpty(UnityData.ActiveCombo) ? "G" : UnityData.ActiveCombo;
        LoadOverlaySummary = $"{caso}: λG {l[0]:0.##} · λQ {l[1]:0.##} · λEX {l[2]:0.##} · λEY {l[3]:0.##}\n" +
                             (wMax > 0f ? $"Gravedad: banda naranja ∝ w (máx {wMax:0.0} kN/m)\n" : "") +
                             (fx > 0f ? $"EX: flechas verdes, Σ = {fx:0} kN\n" : "") +
                             (fy > 0f ? $"EY: flechas moradas, Σ = {fy:0} kN" : "");
        MarkGeneratedDontSave();
    }

    private void CreateGravityLoads(StructureData data, float lG, float lQ, out float wMax)
    {
        wMax = 0f;
        if (data.elements == null || (Mathf.Abs(lG) < 1e-6f && Mathf.Abs(lQ) < 1e-6f)) return;
        var loads = new List<(ElementData e, Vector3 a, Vector3 b, float w)>();
        foreach (ElementData e in data.elements)
        {
            if (e.type != "viga" && e.type != "rigido") continue;
            if (UnityData.IsRemoved(e.id) || !nodes.TryGetValue(e.nodeI, out Vector3 a) || !nodes.TryGetValue(e.nodeJ, out Vector3 b)) continue;
            float len = Vector3.Distance(a, b);
            if (len < 0.05f || Mathf.Abs(a.y - b.y) > 0.05f) continue;
            float w = (lG * (e.deadLoad + e.selfWeight_kN) + lQ * e.liveLoad) / len;   // kN/m, hacia abajo > 0
            if (Mathf.Abs(w) < 0.05f) continue;
            loads.Add((e, a, b, w));
            wMax = Mathf.Max(wMax, Mathf.Abs(w));
        }
        if (wMax <= 0f) return;
        // una malla por piso (para el filtro de piso): banda vertical + flechas
        var byFloor = new Dictionary<string, (List<Vector3> fv, List<Color> fc, List<int> fi, List<Vector3> lv, List<Color> lc, List<int> li)>();
        Color fill = new Color(GravityColor.r, GravityColor.g, GravityColor.b, 0.22f);
        foreach (var (e, a, b, w) in loads)
        {
            string floor = NormalizeFloor(e.piso);
            if (!byFloor.TryGetValue(floor, out var m))
            {
                m = (new List<Vector3>(), new List<Color>(), new List<int>(), new List<Vector3>(), new List<Color>(), new List<int>());
                byFloor[floor] = m;
            }
            float h = 1.2f * Mathf.Abs(w) / wMax;
            Vector3 up = Vector3.up * h * Mathf.Sign(w);
            int f0 = m.fv.Count;
            m.fv.Add(a); m.fv.Add(b); m.fv.Add(b + up); m.fv.Add(a + up);
            for (int k = 0; k < 4; k++) m.fc.Add(fill);
            m.fi.AddRange(new[] { f0, f0 + 1, f0 + 2, f0, f0 + 2, f0 + 3, f0, f0 + 2, f0 + 1, f0, f0 + 3, f0 + 2 });
            void Seg(Vector3 p, Vector3 q) { m.lv.Add(p); m.lv.Add(q); m.lc.Add(GravityColor); m.lc.Add(GravityColor); m.li.Add(m.lv.Count - 2); m.li.Add(m.lv.Count - 1); }
            Seg(a + up, b + up);
            float len = Vector3.Distance(a, b);
            int n = Mathf.Clamp(Mathf.RoundToInt(len / 1.2f), 2, 12);
            Vector3 along = (b - a).normalized;
            float head = Mathf.Min(0.18f, 0.35f * h);
            for (int k = 0; k <= n; k++)
            {
                Vector3 p = Vector3.Lerp(a, b, k / (float)n);
                Seg(p + up, p);
                Seg(p, p + up.normalized * head + along * head * 0.6f);
                Seg(p, p + up.normalized * head - along * head * 0.6f);
            }
        }
        foreach (var kv in byFloor)
        {
            GameObject f = MeshObject("Cargas_gravedad_relleno_" + kv.Key, kv.Value.fv, kv.Value.fc, kv.Value.fi, MeshTopology.Triangles, OverlayFill());
            GameObject l = MeshObject("Cargas_gravedad_flechas_" + kv.Key, kv.Value.lv, kv.Value.lc, kv.Value.li, MeshTopology.Lines, OverlayLine());
            loadObjects.Add(f); loadObjects.Add(l);
            RegisterFloor(f, kv.Key); RegisterFloor(l, kv.Key);
        }
    }

    private void CreateSeismicArrows(StructureData data, float lEX, float lEY, out float sumX, out float sumY)
    {
        sumX = sumY = 0f;
        if (data.diafragmasSismo == null) return;
        float fMax = 0f;
        foreach (DiafragmaData d in data.diafragmasSismo)
            fMax = Mathf.Max(fMax, Mathf.Abs(lEX * d.F_EX_kN), Mathf.Abs(lEY * d.F_EY_kN));
        if (fMax <= 0f) return;
        foreach (DiafragmaData d in data.diafragmasSismo)
        {
            if (!nodes.TryGetValue(d.maestro, out Vector3 master)) continue;
            float fx = lEX * d.F_EX_kN, fy = lEY * d.F_EY_kN;
            sumX += Mathf.Abs(fx); sumY += Mathf.Abs(fy);
            // la flecha llega al borde del diafragma (fuera de la estructura) y una linea la une al nodo maestro
            // EX: paralela a la cara sur (y0), visible desde la camara ISO; EY: llega a la cara sur
            if (Mathf.Abs(fx) > 1e-3f)
                SeismicArrow(d, master, new Vector3(d.cm_x, d.z, d.y0 - 2.5f), Vector3.right * Mathf.Sign(fx), Mathf.Abs(fx), fMax, ExColor, "EX");
            if (Mathf.Abs(fy) > 1e-3f)
                SeismicArrow(d, master, new Vector3(master.x, d.z, fy > 0f ? d.y0 - 0.4f : d.y1 + 0.4f), Vector3.forward * Mathf.Sign(fy), Mathf.Abs(fy), fMax, EyColor, "EY");
        }
    }

    private void SeismicArrow(DiafragmaData d, Vector3 master, Vector3 tip, Vector3 dir, float f, float fMax, Color color, string caso)
    {
        float len = 2f + 7f * f / fMax;
        Vector3 tail = tip - dir * len;
        Vector3 bodyEnd = tip - dir * 0.6f;
        Material mat = CreateMaterial(color);
        GameObject body = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        body.name = $"Sismo_{caso}_{d.edificio}_{d.piso}";
        body.transform.SetParent(transform);
        body.transform.position = (tail + bodyEnd) * 0.5f;
        body.transform.rotation = Quaternion.FromToRotation(Vector3.up, dir);
        body.transform.localScale = new Vector3(0.22f, Vector3.Distance(tail, bodyEnd) * 0.5f, 0.22f);
        body.GetComponent<Renderer>().material = mat;
        body.GetComponent<Collider>().enabled = false;
        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cube);
        head.name = body.name + "_punta";
        head.transform.SetParent(transform);
        head.transform.position = tip - dir * 0.3f;
        head.transform.rotation = Quaternion.LookRotation(dir) * Quaternion.Euler(0f, 45f, 0f);
        head.transform.localScale = new Vector3(0.6f, 0.6f, 0.6f);
        head.GetComponent<Renderer>().material = mat;
        head.GetComponent<Collider>().enabled = false;
        GameObject guide = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        guide.name = body.name + "_al_maestro";
        guide.transform.SetParent(transform);
        guide.transform.position = (tip + master) * 0.5f;
        guide.transform.rotation = Quaternion.FromToRotation(Vector3.up, (master - tip).normalized);
        guide.transform.localScale = new Vector3(0.04f, Vector3.Distance(tip, master) * 0.5f, 0.04f);
        guide.GetComponent<Renderer>().material = CreateMaterial(new Color(color.r, color.g, color.b, 0.6f));
        guide.GetComponent<Collider>().enabled = false;
        GameObject label = Label(body.name + "_valor", $"{caso} {f:0} kN (N{d.maestro})", tail + Vector3.up * 0.8f, color, 0.2f, false);
        foreach (GameObject go in new[] { body, head, guide, label }) { loadObjects.Add(go); RegisterFloor(go, d.piso); }
    }
}
