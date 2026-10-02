using System.Collections.Generic;
using System.IO;
using UnityEngine;

/// <summary>
/// CARGA EN ELEMENTO: carga puntual o distribuida sobre el elemento que el
/// usuario elige por id/tag (o el seleccionado con click).
/// Al elegir el elemento se ejecuta scripts/carga_elemento.py (OpenSees), que
/// entrega los 12 casos unitarios del elemento; luego UnityData.ApplyElementLoad
/// combina esos casos en vivo para cualquier magnitud, posicion, tramo y
/// direccion (resultado exacto, modelo lineal). Requiere Python (editor / PC).
/// </summary>
public class ElementLoadPanel : MonoBehaviour
{
    private StructureViewer viewer;
    private DiagramController diagrams;

    private bool active;
    private string elementText = "";
    private string status = "Escribe el id/tag o usa el elemento seleccionado.";
    private ElementLoadCases cases;
    private readonly Dictionary<int, ElementLoadCases> cache = new Dictionary<int, ElementLoadCases>();

    private int loadType;         // 0 = puntual, 1 = distribuida
    private int direction;        // 0 = -Z, 1 = +X, 2 = +Y
    private float P = 50f;
    private string pText = "50";
    private float w = 10f;
    private string wText = "10";
    private float a;
    private float x1, x2;
    private bool dirty;
    private float lastRefresh;
    private UnityData.ElementLoadState state;

#if UNITY_EDITOR || UNITY_STANDALONE
    private System.Diagnostics.Process process;
#endif
    private int pendingElement = -1;
    private string pendingOut;
    private float processStart;

    private GameObject visuals;
    private Material arrowMaterial;

    private static readonly string[] TypeLabels = { "Puntual", "Distribuida" };
    private static readonly string[] DirLabels = { "-Z (gravedad)", "+X", "+Y" };
    private const float RefreshInterval = 0.08f;
    private const float CollapsedH = 58f;

    public void Initialize(StructureViewer owner, DiagramController diagramController)
    {
        viewer = owner;
        diagrams = diagramController;
    }

    private Vector3 LoadDirection()
    {
        if (direction == 1) return new Vector3(1f, 0f, 0f);
        if (direction == 2) return new Vector3(0f, 1f, 0f);
        return new Vector3(0f, 0f, -1f);
    }

    private void Update()
    {
        PollProcess();
        if (!active || cases == null) return;

        if (UnityData.ActiveCombo != UnityData.ElementLoadComboName)
        {
            Deactivate(false);
            return;
        }
        if (dirty && Time.unscaledTime - lastRefresh >= RefreshInterval)
        {
            Apply();
        }
    }

    // ------------------------------------------------------------------
    // Seleccion del elemento y calculo de los casos unitarios (Python)
    // ------------------------------------------------------------------
    private ElementData FindElement(string key)
    {
        if (UnityData.Structure == null || UnityData.Structure.elements == null) return null;
        key = (key ?? "").Trim();
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (e == null) continue;
            if (e.id.ToString() == key || string.Equals(e.elementTag, key, System.StringComparison.OrdinalIgnoreCase)) return e;
        }
        return null;
    }

    private void RequestElement(string key)
    {
        ElementData e = FindElement(key);
        if (e == null)
        {
            status = $"No existe el elemento '{key}'.";
            return;
        }
        elementText = !string.IsNullOrEmpty(e.elementTag) ? e.elementTag : e.id.ToString();
        if (cache.TryGetValue(e.id, out ElementLoadCases cached))
        {
            UseCases(cached);
            return;
        }
        StartPython(e.id);
    }

    private void StartPython(int elementId)
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        string script = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "scripts", "carga_elemento.py"));
        if (!File.Exists(script))
        {
            status = "No encontre scripts/carga_elemento.py";
            return;
        }
        pendingOut = Path.Combine(Application.temporaryCachePath, $"carga_elemento_{elementId}.json");
        if (File.Exists(pendingOut)) File.Delete(pendingOut);
        foreach (string exe in new[] { "python", "py" })
        {
            try
            {
                var info = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = exe,
                    Arguments = $"-X utf8 \"{script}\" --element {elementId} --out \"{pendingOut}\"",
                    WorkingDirectory = Path.GetDirectoryName(script),
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                process = System.Diagnostics.Process.Start(info);
                pendingElement = elementId;
                processStart = Time.unscaledTime;
                status = "Calculando casos unitarios en OpenSees...";
                return;
            }
            catch (System.Exception)
            {
                process = null;
            }
        }
        status = "No se pudo ejecutar Python (python/py en el PATH).";
#else
        status = "La carga en elemento requiere Python: solo disponible en el editor o en PC.";
#endif
    }

    private void PollProcess()
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        if (process == null) return;
        if (!process.HasExited)
        {
            if (Time.unscaledTime - processStart > 90f)
            {
                try { process.Kill(); } catch (System.Exception) { }
                process = null;
                status = "Tiempo de calculo excedido.";
            }
            return;
        }
        string err = process.StandardError.ReadToEnd();
        process = null;
        if (!File.Exists(pendingOut))
        {
            status = "Error en carga_elemento.py: " + (string.IsNullOrEmpty(err) ? "sin salida" : err.Split('\n')[0]);
            return;
        }
        ElementLoadCases loaded = JsonUtility.FromJson<ElementLoadCases>(File.ReadAllText(pendingOut));
        if (loaded == null || !string.IsNullOrEmpty(loaded.error) || loaded.unitCases == null)
        {
            status = loaded != null && !string.IsNullOrEmpty(loaded.error) ? loaded.error : "Respuesta invalida de Python.";
            return;
        }
        cache[pendingElement] = loaded;
        UseCases(loaded);
#endif
    }

    private void UseCases(ElementLoadCases loaded)
    {
        cases = loaded;
        a = cases.length * 0.5f;
        x1 = 0f;
        x2 = cases.length;
        status = $"{cases.tag} ({cases.type}, L = {cases.length:0.00} m) listo.";
        active = true;
        CreateVisuals();
        Apply();
        if (diagrams != null && diagrams.CurrentResultName() == "None" && viewer != null)
        {
            viewer.SetResult("Momento");
        }
    }

    private void Deactivate(bool restoreCombo)
    {
        active = false;
        state = null;
        UnityData.ElementLoad = null;
        DestroyVisuals();
        if (restoreCombo && viewer != null) viewer.RestoreSelectedCombo();
    }

    private void Apply()
    {
        if (cases == null) return;
        state = UnityData.ApplyElementLoad(cases, loadType == 1, LoadDirection(), P, a, w, x1, x2);
        dirty = false;
        lastRefresh = Time.unscaledTime;
        if (diagrams != null) diagrams.Refresh();
        UpdateVisuals();
    }

    // ------------------------------------------------------------------
    // Visual: flecha (puntual) o fila de flechas + barra (distribuida)
    // ------------------------------------------------------------------
    private void CreateVisuals()
    {
        DestroyVisuals();
        visuals = new GameObject("CargaElemento_Visual");
        if (arrowMaterial == null)
        {
            Shader shader = Shader.Find("Standard");
            if (shader == null) shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) shader = Shader.Find("Sprites/Default");
            arrowMaterial = new Material(shader) { color = new Color(0.75f, 0.3f, 1f, 1f) };
        }
    }

    private static Vector3 ToUnity(Vector3 m)
    {
        return new Vector3(m.x, m.z, m.y);
    }

    private void AddArrow(Vector3 tipUnity, Vector3 dirUnity, float length)
    {
        Vector3 back = -dirUnity.normalized;
        GameObject shaft = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        shaft.transform.SetParent(visuals.transform, false);
        shaft.transform.position = tipUnity + back * (0.35f + length * 0.5f);
        shaft.transform.rotation = Quaternion.FromToRotation(Vector3.up, back);
        shaft.transform.localScale = new Vector3(0.1f, length * 0.5f, 0.1f);
        Prepare(shaft);

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cube);
        head.transform.SetParent(visuals.transform, false);
        head.transform.position = tipUnity + back * 0.2f;
        head.transform.rotation = Quaternion.FromToRotation(Vector3.up, back) * Quaternion.Euler(45f, 0f, 45f);
        head.transform.localScale = new Vector3(0.28f, 0.28f, 0.28f);
        Prepare(head);
    }

    private void Prepare(GameObject obj)
    {
        obj.GetComponent<Renderer>().material = arrowMaterial;
        Collider col = obj.GetComponent<Collider>();
        if (col != null) Destroy(col);
    }

    private void UpdateVisuals()
    {
        if (state == null || visuals == null) return;
        for (int i = visuals.transform.childCount - 1; i >= 0; i--) Destroy(visuals.transform.GetChild(i).gameObject);

        Vector3 dirU = ToUnity(state.dir);
        Vector3 axis = (state.pJ - state.pI) / state.L;
        if (!state.distributed)
        {
            AddArrow(ToUnity(state.pI + axis * state.a), dirU, 1.8f);
        }
        else
        {
            int n = Mathf.Clamp(Mathf.RoundToInt((state.x2 - state.x1) / 0.8f) + 1, 2, 12);
            for (int k = 0; k < n; k++)
            {
                float x = Mathf.Lerp(state.x1, state.x2, n == 1 ? 0.5f : k / (float)(n - 1));
                AddArrow(ToUnity(state.pI + axis * x), dirU, 1.2f);
            }
            Vector3 s0 = ToUnity(state.pI + axis * state.x1) - dirU.normalized * 1.9f;
            Vector3 s1 = ToUnity(state.pI + axis * state.x2) - dirU.normalized * 1.9f;
            GameObject bar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            bar.transform.SetParent(visuals.transform, false);
            bar.transform.position = (s0 + s1) * 0.5f;
            Vector3 along = s1 - s0;
            if (along.sqrMagnitude > 1e-6f) bar.transform.rotation = Quaternion.LookRotation(along.normalized, Vector3.up);
            bar.transform.localScale = new Vector3(0.08f, 0.08f, Mathf.Max(0.05f, along.magnitude));
            Prepare(bar);
        }
    }

    private void DestroyVisuals()
    {
        if (visuals != null) Destroy(visuals);
        visuals = null;
    }

    private void OnDestroy()
    {
        DestroyVisuals();
#if UNITY_EDITOR || UNITY_STANDALONE
        if (process != null && !process.HasExited)
        {
            try { process.Kill(); } catch (System.Exception) { }
        }
#endif
    }

    // ------------------------------------------------------------------
    // Panel (misma columna que la carga movil)
    // ------------------------------------------------------------------
    private bool TryParse(string text, out float value)
    {
        return float.TryParse(text.Replace(',', '.'), System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture, out value);
    }

    private void OnGUI()
    {
        if (ViewerUI.Active && ViewerUI.ActiveTab != ViewerUI.TabCargas) return;
        UiTheme.ApplyScale();
        // requiere Python/OpenSees: no se muestra en el celular
        if (!PythonJob.Available) return;
        // mientras la carga movil esta activa, este panel se oculta
        if (UnityData.ActiveCombo == UnityData.MovingLoadComboName) return;
        // con el modelo modificado (elementos quitados) sus casos unitarios ya no aplican
        if (UnityData.IsModelModified) return;

        Rect left = UiTheme.LeftArea();
        float x = left.x;
        float w0 = left.width;
        float y = left.yMax + 14f;
        bool movingAvailable = UnityData.GetMovingLoadData() != null;
        if (!active && movingAvailable) y += CollapsedH + 8f;   // bajo el recuadro de carga movil
        float ix = x + 10f;
        float iw = w0 - 20f;

        if (!active)
        {
            float hc = 106f;
            UiTheme.GUIBox(new Rect(x, y, w0, hc), "CARGA EN ELEMENTO");
            float iy = y + 28f;
            GUI.Label(new Rect(ix, iy, 58f, 20f), "id/tag", UiTheme.DimLabel);
            elementText = GUI.TextField(new Rect(ix + 58f, iy, 110f, 20f), elementText);
            bool busy = pendingElement >= 0 && IsBusy();
            GUI.enabled = !busy;
            if (GUI.Button(new Rect(ix + 174f, iy, iw - 174f, 20f), "Cargar")) RequestElement(elementText);
            iy += 24f;
            var picker = FindObjectOfType<ElementPicker>();
            bool hasSel = picker != null && picker.Selected != null && picker.Selected.data != null;
            GUI.enabled = !busy && hasSel;
            if (GUI.Button(new Rect(ix, iy, iw, 20f), hasSel ? "Usar seleccionado: " + picker.Selected.data.elementTag : "Selecciona un elemento con click"))
            {
                RequestElement(picker.Selected.data.id.ToString());
            }
            GUI.enabled = true;
            iy += 24f;
            GUI.Label(new Rect(ix, iy, iw, 18f), status, UiTheme.DimLabel);
            return;
        }

        float h = Mathf.Min(Mathf.Max(300f, UiTheme.ScreenH - y - 12f), 378f);
        UiTheme.GUIBox(new Rect(x, y, w0, h), "CARGA EN ELEMENTO · " + cases.tag);
        float jy = y + 28f;

        int nextType = GUI.Toolbar(new Rect(ix, jy, iw, 20f), loadType, TypeLabels);
        if (nextType != loadType) { loadType = nextType; dirty = true; }
        jy += 24f;
        GUI.Label(new Rect(ix, jy, 58f, 20f), "Direccion", UiTheme.DimLabel);
        int nextDir = GUI.Toolbar(new Rect(ix + 62f, jy, iw - 62f, 20f), direction, DirLabels);
        if (nextDir != direction) { direction = nextDir; dirty = true; }
        jy += 26f;

        float L = cases.length;
        if (loadType == 0)
        {
            GUI.Label(new Rect(ix, jy, 58f, 20f), "P [kN]", UiTheme.DimLabel);
            string next = GUI.TextField(new Rect(ix + 62f, jy, 80f, 20f), pText);
            if (next != pText) { pText = next; if (TryParse(pText, out float v)) { P = v; dirty = true; } }
            jy += 24f;
            GUI.Label(new Rect(ix, jy, iw, 18f), $"Posicion a = {a:0.00} m desde el nodo I (L = {L:0.00} m)", UiTheme.Label);
            jy += 20f;
            float na = GUI.HorizontalSlider(new Rect(ix, jy, iw, 18f), a, 0f, L);
            if (Mathf.Abs(na - a) > 1e-4f) { a = na; dirty = true; }
            jy += 24f;
        }
        else
        {
            GUI.Label(new Rect(ix, jy, 58f, 20f), "w [kN/m]", UiTheme.DimLabel);
            string next = GUI.TextField(new Rect(ix + 62f, jy, 80f, 20f), wText);
            if (next != wText) { wText = next; if (TryParse(wText, out float v)) { w = v; dirty = true; } }
            if (GUI.Button(new Rect(ix + 150f, jy, iw - 150f, 20f), "Todo el largo")) { x1 = 0f; x2 = L; dirty = true; }
            jy += 24f;
            GUI.Label(new Rect(ix, jy, iw, 18f), $"Tramo x1 = {x1:0.00} m  ->  x2 = {x2:0.00} m", UiTheme.Label);
            jy += 20f;
            float n1 = GUI.HorizontalSlider(new Rect(ix, jy, iw, 16f), x1, 0f, L);
            if (Mathf.Abs(n1 - x1) > 1e-4f) { x1 = Mathf.Min(n1, x2); dirty = true; }
            jy += 18f;
            float n2 = GUI.HorizontalSlider(new Rect(ix, jy, iw, 16f), x2, 0f, L);
            if (Mathf.Abs(n2 - x2) > 1e-4f) { x2 = Mathf.Max(n2, x1); dirty = true; }
            jy += 22f;
        }

        if (state != null)
        {
            float total = state.total.magnitude;
            Vector3 r = state.sumR;
            GUI.Label(new Rect(ix, jy, iw, 18f), $"Carga total = {total:0.00} kN", UiTheme.Label);
            jy += 18f;
            GUI.Label(new Rect(ix, jy, iw, 18f), $"Nodo I: F = ({state.qI[0]:0.0}, {state.qI[1]:0.0}, {state.qI[2]:0.0}) kN", UiTheme.DimLabel);
            jy += 17f;
            GUI.Label(new Rect(ix, jy, iw, 18f), $"Nodo J: F = ({state.qJ[0]:0.0}, {state.qJ[1]:0.0}, {state.qJ[2]:0.0}) kN", UiTheme.DimLabel);
            jy += 17f;
            GUI.Label(new Rect(ix, jy, iw, 18f), $"Reacciones = ({r.x:0.00}, {r.y:0.00}, {r.z:0.00}) kN", UiTheme.Label);
            jy += 18f;
            float err = (r + state.total).magnitude;
            GUI.Label(new Rect(ix, jy, iw, 18f),
                err < 1e-3f * Mathf.Max(1f, total) ? "OK: reacciones = - carga (se conserva)" : $"AVISO: desbalance {err:0.000} kN",
                UiTheme.DimLabel);
            jy += 22f;
        }

        if (GUI.Button(new Rect(ix, jy, 96f, 20f), "Momento") && viewer != null) viewer.SetResult("Momento");
        if (GUI.Button(new Rect(ix + 100f, jy, 96f, 20f), "Deformada") && viewer != null) viewer.SetResult("Deformada");
        if (GUI.Button(new Rect(ix + 200f, jy, iw - 200f, 20f), "Cerrar")) Deactivate(true);
        jy += 24f;
        if (GUI.Button(new Rect(ix, jy, iw, 20f), "Cambiar elemento"))
        {
            Deactivate(true);
        }
    }

    private bool IsBusy()
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        return process != null;
#else
        return false;
#endif
    }
}
