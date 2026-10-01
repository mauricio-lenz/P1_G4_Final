using System.Collections.Generic;
using System.IO;
using UnityEngine;

/// <summary>
/// QUITAR ELEMENTO: el usuario indica uno o mas elementos (id/tag o click),
/// Unity ejecuta scripts/quitar_elemento.py, que reanaliza en OpenSees
/// G/Q/EX/EY/C1/C2/C3 sin esos elementos, y reemplaza en memoria los
/// resultados: diagramas, deformada y P-M pasan a mostrar el modelo
/// modificado. "Restaurar" vuelve al modelo original. No toca archivos.
/// </summary>
public class ElementRemovalPanel : MonoBehaviour
{
    private StructureViewer viewer;
    private DiagramController diagrams;

    private string inputText = "";
    private string status = "Indica los elementos a quitar (id/tag separados por coma).";
    private readonly List<string> pending = new List<string>();   // tags del modelo modificado
    private readonly PythonJob job = new PythonJob();
    private GameObject ghosts;
    private Material ghostMaterial;
    private Vector2 scroll;

    private string comparedCombo;
    private float fixedScaleValue = 300f;
    private float lastDiagramRefresh;
    private readonly List<string> comparison = new List<string>();
    private string dispSummary = "";

    private const float MovingCollapsedH = 58f;
    private const float ElementLoadCollapsedH = 106f;

    public void Initialize(StructureViewer owner, DiagramController diagramController)
    {
        viewer = owner;
        diagrams = diagramController;
    }

    private void Update()
    {
        if (refreshPending && Time.unscaledTime - lastDiagramRefresh >= 0.08f)
        {
            refreshPending = false;
            lastDiagramRefresh = Time.unscaledTime;
            if (diagrams != null) diagrams.Refresh();
        }
        if (job.Poll())
        {
            OnJobFinished();
        }
        if (UnityData.IsModelModified && CurrentCompareCombo() != comparedCombo)
        {
            BuildComparison();
        }
    }

    // ------------------------------------------------------------------
    // Reanalisis
    // ------------------------------------------------------------------
    private ElementData FindElement(string key)
    {
        key = (key ?? "").Trim();
        if (UnityData.Structure == null || UnityData.Structure.elements == null || key.Length == 0) return null;
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (e != null && (e.id.ToString() == key || string.Equals(e.elementTag, key, System.StringComparison.OrdinalIgnoreCase))) return e;
        }
        return null;
    }

    private void AddToInput(string tag)
    {
        var parts = new List<string>(inputText.Split(','));
        parts.RemoveAll(p => p.Trim().Length == 0);
        if (!parts.Exists(p => string.Equals(p.Trim(), tag, System.StringComparison.OrdinalIgnoreCase))) parts.Add(tag);
        inputText = string.Join(", ", parts);
    }

    private void RunRemoval(IEnumerable<string> keys)
    {
        var tags = new List<string>();
        var ids = new List<string>();
        foreach (string k in keys)
        {
            if (k.Trim().Length == 0) continue;
            ElementData e = FindElement(k);
            if (e == null)
            {
                status = $"No existe el elemento '{k.Trim()}'.";
                return;
            }
            string tag = !string.IsNullOrEmpty(e.elementTag) ? e.elementTag : e.id.ToString();
            if (!tags.Contains(tag)) { tags.Add(tag); ids.Add(e.id.ToString()); }
        }
        if (ids.Count == 0)
        {
            status = "No indicaste ningun elemento.";
            return;
        }
        pending.Clear();
        pending.AddRange(tags);
        if (job.Start("quitar_elemento.py", "--elements " + string.Join(",", ids), "quitar_elemento.json"))
        {
            status = "Reanalizando en OpenSees (7 casos) sin: " + string.Join(", ", tags) + " ...";
        }
        else
        {
            status = job.Error;
        }
    }

    private void OnJobFinished()
    {
        if (!string.IsNullOrEmpty(job.Error))
        {
            status = job.Error;
            return;
        }
        ElementRemovalResult result = JsonUtility.FromJson<ElementRemovalResult>(File.ReadAllText(job.OutputPath));
        if (result == null || !string.IsNullOrEmpty(result.error) || result.displacements == null)
        {
            status = result != null && !string.IsNullOrEmpty(result.error) ? result.error : "Respuesta invalida de Python.";
            return;
        }
        UnityData.ApplyRemovalResults(result);
        inputText = "";
        CreateGhosts();
        if (viewer != null) viewer.RestoreSelectedCombo();
        comparedCombo = null;
        BuildComparison();
        bool allOk = true;
        foreach (RemovalCaseState s in result.estado) allOk &= s.ok;
        status = allOk ? "Reanalisis completo: el viewer muestra el modelo modificado."
                       : "ATENCION: algun caso no convergio (posible mecanismo).";
    }

    private bool refreshPending;

    private void RefreshDiagrams()
    {
        // se aplica en Update, limitado a ~12 veces por segundo al arrastrar el slider
        refreshPending = true;
    }

    private void Restore()
    {
        job.Kill();
        UnityData.DeformedScaleOverride = 0f;
        UnityData.RestoreOriginalModel();
        DestroyGhosts();
        pending.Clear();
        comparison.Clear();
        comparedCombo = null;
        if (viewer != null) viewer.RestoreSelectedCombo();
        status = "Modelo original restaurado.";
    }

    // ------------------------------------------------------------------
    // Comparacion antes / despues para el combo activo
    // ------------------------------------------------------------------
    private string CurrentCompareCombo()
    {
        string c = UnityData.ActiveCombo;
        return System.Array.IndexOf(UnityData.AnalysisCombos, c) >= 0 ? c : "C1";
    }

    private static float Metric(ElementData e, float[] f)
    {
        // f = fuerzas de extremo locales: columnas/arriostres -> |N|, vigas -> max |M| en los extremos
        if (f == null || f.Length < 12) return 0f;
        if (e.type == "columna" || e.type == "arriostre") return Mathf.Max(Mathf.Abs(f[0]), Mathf.Abs(f[6]));
        float mi = Mathf.Sqrt(f[4] * f[4] + f[5] * f[5]);
        float mj = Mathf.Sqrt(f[10] * f[10] + f[11] * f[11]);
        return Mathf.Max(mi, mj);
    }

    private void BuildComparison()
    {
        comparedCombo = CurrentCompareCombo();
        comparison.Clear();
        if (!UnityData.IsModelModified) return;

        var rows = new List<KeyValuePair<float, string>>();
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (e == null || UnityData.IsRemoved(e.id)) continue;
            float before = Metric(e, UnityData.GetOriginalElementForces(comparedCombo, e.id));
            float after = Metric(e, UnityData.GetElementForces(comparedCombo, e.id));
            float delta = after - before;
            if (delta <= 1e-3f) continue;
            string unit = e.type == "viga" ? "|M|" : "|N|";
            string ratio = before > 1e-3f ? $"x{after / before:0.00}" : "nuevo";
            rows.Add(new KeyValuePair<float, string>(delta,
                $"{e.elementTag}: {unit} {before:0.0} -> {after:0.0} ({ratio})"));
        }
        rows.Sort((x, y) => y.Key.CompareTo(x.Key));
        for (int i = 0; i < Mathf.Min(6, rows.Count); i++) comparison.Add(rows[i].Value);

        float maxDu = 0f;
        int maxNode = -1;
        foreach (NodeData n in UnityData.Structure.nodes)
        {
            float du = (UnityData.GetNodeDisplacement(comparedCombo, n.id) - UnityData.GetOriginalNodeDisplacement(comparedCombo, n.id)).magnitude;
            if (du > maxDu) { maxDu = du; maxNode = n.id; }
        }
        dispSummary = maxNode >= 0 ? $"Mayor cambio de desplazamiento: nodo {maxNode}, {maxDu * 1000f:0.00} mm" : "";
    }

    // ------------------------------------------------------------------
    // Visual: elementos quitados como "fantasmas" rojos
    // ------------------------------------------------------------------
    private void CreateGhosts()
    {
        DestroyGhosts();
        ghosts = new GameObject("ElementosQuitados");
        if (ghostMaterial == null)
        {
            Shader shader = Shader.Find("Sprites/Default");
            if (shader == null) shader = Shader.Find("Standard");
            ghostMaterial = new Material(shader) { color = new Color(1f, 0.15f, 0.15f, 0.45f) };
        }
        var nodes = new Dictionary<int, Vector3>();
        foreach (NodeData n in UnityData.Structure.nodes) nodes[n.id] = new Vector3(n.x, n.z, n.y);
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (e == null || !UnityData.IsRemoved(e.id)) continue;
            if (!nodes.TryGetValue(e.nodeI, out Vector3 a) || !nodes.TryGetValue(e.nodeJ, out Vector3 b)) continue;
            GameObject g = GameObject.CreatePrimitive(PrimitiveType.Cube);
            g.name = "Quitado_" + e.elementTag;
            g.transform.SetParent(ghosts.transform, false);
            g.transform.position = (a + b) * 0.5f;
            g.transform.rotation = Quaternion.LookRotation((b - a).normalized, Mathf.Abs((b - a).normalized.y) > 0.9f ? Vector3.forward : Vector3.up);
            float t = Mathf.Max(e.width_m, 0.3f) * 1.15f;
            g.transform.localScale = new Vector3(t, t, (b - a).magnitude);
            g.GetComponent<Renderer>().material = ghostMaterial;
            Collider col = g.GetComponent<Collider>();
            if (col != null) Destroy(col);
        }
    }

    private void DestroyGhosts()
    {
        if (ghosts != null) Destroy(ghosts);
        ghosts = null;
    }

    private void OnDestroy()
    {
        job.Kill();
        DestroyGhosts();
    }

    // ------------------------------------------------------------------
    // Panel
    // ------------------------------------------------------------------
    private void OnGUI()
    {
        UiTheme.ApplyScale();
        // requiere Python/OpenSees: no se muestra en el celular
        if (!PythonJob.Available) return;
        // mientras una carga movil / en elemento esta activa, este panel se oculta
        if (UnityData.ActiveCombo == UnityData.MovingLoadComboName || UnityData.ActiveCombo == UnityData.ElementLoadComboName) return;

        Rect left = UiTheme.LeftArea();
        float x = left.x;
        float w0 = left.width;
        float y = left.yMax + 14f;
        float ix = x + 10f;
        float iw = w0 - 20f;
        var picker = FindObjectOfType<ElementPicker>();
        bool hasSel = picker != null && picker.Selected != null && picker.Selected.data != null;

        if (!UnityData.IsModelModified)
        {
            if (UnityData.GetMovingLoadData() != null) y += MovingCollapsedH + 8f;
            y += ElementLoadCollapsedH + 8f;
            UiTheme.GUIBox(new Rect(x, y, w0, 106f), "QUITAR ELEMENTO (REANALISIS)");
            float iy = y + 28f;
            GUI.enabled = !job.Running;
            inputText = GUI.TextField(new Rect(ix, iy, iw - 128f, 20f), inputText);
            if (GUI.Button(new Rect(ix + iw - 124f, iy, 124f, 20f), "Quitar y analizar"))
            {
                RunRemoval(inputText.Split(','));
            }
            iy += 24f;
            GUI.enabled = !job.Running && hasSel;
            if (GUI.Button(new Rect(ix, iy, iw, 20f), hasSel ? "Agregar seleccionado: " + picker.Selected.data.elementTag : "Selecciona un elemento con click"))
            {
                AddToInput(picker.Selected.data.elementTag);
            }
            GUI.enabled = true;
            iy += 24f;
            GUI.Label(new Rect(ix, iy, iw, 18f), status, UiTheme.DimLabel);
            return;
        }

        // Modelo modificado: resumen del reanalisis
        ElementRemovalResult r = UnityData.Removal;
        float h = Mathf.Min(Mathf.Max(340f, UiTheme.ScreenH - y - 12f), 450f);
        UiTheme.GUIBox(new Rect(x, y, w0, h), "MODELO MODIFICADO (REANALISIS)");
        float jy = y + 28f;
        var tags = new List<string>();
        foreach (RemovedElementInfo e in r.removed) tags.Add(e.tag);
        GUI.Label(new Rect(ix, jy, iw, 18f), "Quitados: " + string.Join(", ", tags), UiTheme.Label);
        jy += 20f;
        float gA = Mathf.Abs(r.G_aplicada_kN);
        GUI.Label(new Rect(ix, jy, iw, 18f), $"G aplicada {gA:0.0} kN | reaccion {r.G_reaccion_kN:0.0} kN", UiTheme.DimLabel);
        jy += 17f;
        if (r.carga_perdida_kN > 0.01f)
        {
            GUI.Label(new Rect(ix, jy, iw, 18f), $"AVISO: {r.carga_perdida_kN:0.0} kN quedan en nodos sin elementos", UiTheme.DimLabel);
            jy += 17f;
        }
        bool allOk = true;
        foreach (RemovalCaseState s in r.estado) allOk &= s.ok;
        GUI.Label(new Rect(ix, jy, iw, 18f), allOk ? "Los 7 casos convergieron (estructura estable)." : "ATENCION: algun caso no convergio (mecanismo).", UiTheme.DimLabel);
        jy += 20f;

        GUI.Label(new Rect(ix, jy, iw, 18f), $"Mayores aumentos de esfuerzo ({comparedCombo}):", UiTheme.Header);
        jy += 20f;
        float listH = Mathf.Max(52f, h - (jy - y) - 158f);
        scroll = GUI.BeginScrollView(new Rect(ix, jy, iw, listH), scroll, new Rect(0f, 0f, iw - 18f, Mathf.Max(listH, comparison.Count * 17f + 4f)));
        for (int i = 0; i < comparison.Count; i++)
        {
            GUI.Label(new Rect(0f, i * 17f, iw - 18f, 17f), comparison[i], UiTheme.Label);
        }
        if (comparison.Count == 0) GUI.Label(new Rect(0f, 0f, iw - 18f, 17f), "Sin aumentos relevantes.", UiTheme.DimLabel);
        GUI.EndScrollView();
        jy += listH + 4f;
        GUI.Label(new Rect(ix, jy, iw, 18f), dispSummary, UiTheme.DimLabel);
        jy += 20f;

        // Deformada: comparar original (naranjo) vs modificada (verde), misma escala
        bool nextCompare = GUI.Toggle(new Rect(ix, jy, iw - 104f, 20f), UnityData.CompareDeformed, " Comparar deformada (naranjo = original)");
        if (nextCompare != UnityData.CompareDeformed)
        {
            UnityData.CompareDeformed = nextCompare;
            RefreshDiagrams();
        }
        if (GUI.Button(new Rect(ix + iw - 100f, jy, 100f, 20f), "Ver deformada") && viewer != null) viewer.SetResult("Deformada");
        jy += 22f;
        bool fixedScale = UnityData.DeformedScaleOverride > 0f;
        bool nextFixed = GUI.Toggle(new Rect(ix, jy, 110f, 20f), fixedScale, " Escala fija");
        if (nextFixed != fixedScale)
        {
            UnityData.DeformedScaleOverride = nextFixed ? fixedScaleValue : 0f;
            RefreshDiagrams();
        }
        if (nextFixed)
        {
            float next = GUI.HorizontalSlider(new Rect(ix + 112f, jy + 4f, iw - 180f, 16f), fixedScaleValue, 10f, 2000f);
            if (Mathf.Abs(next - fixedScaleValue) > 0.5f)
            {
                fixedScaleValue = next;
                UnityData.DeformedScaleOverride = fixedScaleValue;
                RefreshDiagrams();
            }
            GUI.Label(new Rect(ix + iw - 62f, jy, 62f, 20f), $"x{fixedScaleValue:0}", UiTheme.DimLabel);
        }
        else
        {
            GUI.Label(new Rect(ix + 112f, jy, iw - 112f, 20f), "(automatica por edificio)", UiTheme.DimLabel);
        }
        jy += 24f;

        GUI.enabled = !job.Running;
        inputText = GUI.TextField(new Rect(ix, jy, iw - 128f, 20f), inputText);
        if (GUI.Button(new Rect(ix + iw - 124f, jy, 124f, 20f), "Quitar tambien"))
        {
            var all = new List<string>(pending);
            all.AddRange(inputText.Split(','));
            RunRemoval(all);
        }
        jy += 24f;
        if (hasSel && GUI.Button(new Rect(ix, jy, iw, 20f), "Agregar seleccionado: " + picker.Selected.data.elementTag))
        {
            AddToInput(picker.Selected.data.elementTag);
        }
        jy += 24f;
        if (GUI.Button(new Rect(ix, jy, iw, 22f), "Restaurar modelo original")) Restore();
        GUI.enabled = true;
        jy += 24f;
        GUI.Label(new Rect(ix, jy, iw, 18f), status, UiTheme.DimLabel);
    }
}
