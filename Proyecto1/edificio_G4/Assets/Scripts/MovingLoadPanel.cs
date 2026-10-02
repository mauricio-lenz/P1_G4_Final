using UnityEngine;

/// <summary>
/// Sidequest semana 5 · CARGA MOVIL.
/// Panel para mover una carga puntual P a lo largo de un recorrido de vigas.
/// La respuesta (deformada, diagramas, reacciones) se obtiene en vivo con
/// UnityData.ApplyMovingLoad, que combina los casos unitarios precalculados
/// en OpenSees (carga_movil.py). P se puede cambiar en cualquier momento.
/// </summary>
public class MovingLoadPanel : MonoBehaviour
{
    private StructureViewer viewer;
    private DiagramController diagrams;

    private bool active;
    private int pathIndex;
    private float s;
    private float P = 50f;
    private string pText = "50";
    private bool playing;
    private float speed = 2f;          // m/s
    private float playDirection = 1f;
    private bool dirty;
    private float lastRefresh;

    private GameObject marker;
    private GameObject pathLine;
    private TextMesh markerLabel;
    private UnityData.MovingLoadState state;

    private const float RefreshInterval = 0.08f;

    public void Initialize(StructureViewer owner, DiagramController diagramController)
    {
        viewer = owner;
        diagrams = diagramController;
        MovingLoadData data = UnityData.GetMovingLoadData();
        if (data != null && data.P_default_kN > 0f)
        {
            P = data.P_default_kN;
            pText = P.ToString("0.##");
        }
        // recorrido inicial: edificio 1, Cielo 1
        if (data != null && data.paths != null)
        {
            for (int i = 0; i < data.paths.Length; i++)
            {
                if (data.paths[i].edificio == "edificio_1" && data.paths[i].nivel == "CIELO_1") { pathIndex = i; break; }
            }
        }
    }

    private MovingLoadPath CurrentPath()
    {
        MovingLoadData data = UnityData.GetMovingLoadData();
        if (data == null || data.paths == null || data.paths.Length == 0) return null;
        pathIndex = Mathf.Clamp(pathIndex, 0, data.paths.Length - 1);
        return data.paths[pathIndex];
    }

    private static string[] BuildingOptions(MovingLoadData data)
    {
        var list = new System.Collections.Generic.List<string>();
        foreach (MovingLoadPath p in data.paths) if (!list.Contains(p.edificio)) list.Add(p.edificio);
        return list.ToArray();
    }

    private static string[] LabelsFor(string[] buildings)
    {
        string[] labels = new string[buildings.Length];
        for (int i = 0; i < buildings.Length; i++) labels[i] = buildings[i].Replace("edificio_", "Edificio ");
        return labels;
    }

    private static string[] FloorOptions(MovingLoadData data, string building)
    {
        var list = new System.Collections.Generic.List<string>();
        foreach (MovingLoadPath p in data.paths) if (p.edificio == building && !list.Contains(p.nivel)) list.Add(p.nivel);
        return list.ToArray();
    }

    /// Cambia al recorrido del edificio y piso pedidos (si el piso no existe, al primero del edificio)
    private void SelectPath(MovingLoadData data, string building, string floor)
    {
        int fallback = -1;
        for (int i = 0; i < data.paths.Length; i++)
        {
            if (data.paths[i].edificio != building) continue;
            if (fallback < 0) fallback = i;
            if (data.paths[i].nivel == floor) { fallback = i; break; }
        }
        if (fallback < 0) return;
        float frac = CurrentPath() != null && CurrentPath().largo > 0f ? s / CurrentPath().largo : 0f;
        pathIndex = fallback;
        s = Mathf.Clamp(frac * data.paths[pathIndex].largo, 0f, data.paths[pathIndex].largo);
        dirty = true;
    }

    private void Update()
    {
        if (!active) return;

        // Si el usuario elige otro combo en la barra superior, se cierra la carga movil
        if (UnityData.ActiveCombo != UnityData.MovingLoadComboName)
        {
            Deactivate(false);
            return;
        }

        MovingLoadPath path = CurrentPath();
        if (path == null) return;

        if (playing)
        {
            s += playDirection * speed * Time.deltaTime;
            if (s >= path.largo) { s = path.largo; playDirection = -1f; }
            if (s <= 0f) { s = 0f; playDirection = 1f; }
            dirty = true;
        }

        if (dirty && Time.unscaledTime - lastRefresh >= RefreshInterval)
        {
            Apply();
        }
    }

    private void Activate()
    {
        MovingLoadPath path = CurrentPath();
        if (path == null) return;
        active = true;
        s = Mathf.Clamp(s, 0f, path.largo);
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
        playing = false;
        state = null;
        UnityData.MovingLoad = null;
        DestroyVisuals();
        if (restoreCombo && viewer != null)
        {
            viewer.RestoreSelectedCombo();
        }
    }

    private void Apply()
    {
        MovingLoadPath path = CurrentPath();
        if (path == null) return;
        state = UnityData.ApplyMovingLoad(path, s, P);
        dirty = false;
        lastRefresh = Time.unscaledTime;
        if (diagrams != null) diagrams.Refresh();
        UpdateVisuals(path);
    }

    // ------------------------------------------------------------------
    // Visual: flecha de la carga y linea del recorrido
    // ------------------------------------------------------------------
    private void CreateVisuals()
    {
        DestroyVisuals();
        Material red = MakeMaterial(new Color(1f, 0.25f, 0.2f, 1f));
        Material orange = MakeMaterial(new Color(1f, 0.65f, 0.1f, 1f));

        marker = new GameObject("CargaMovil_Flecha");
        GameObject shaft = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        shaft.transform.SetParent(marker.transform, false);
        shaft.transform.localScale = new Vector3(0.14f, 0.9f, 0.14f);
        shaft.transform.localPosition = new Vector3(0f, 1.45f, 0f);
        Prepare(shaft, red);

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cube);
        head.transform.SetParent(marker.transform, false);
        head.transform.localScale = new Vector3(0.38f, 0.38f, 0.38f);
        head.transform.localPosition = new Vector3(0f, 0.5f, 0f);
        head.transform.localRotation = Quaternion.Euler(45f, 0f, 45f);
        Prepare(head, red);

        GameObject label = new GameObject("CargaMovil_Etiqueta");
        label.transform.SetParent(marker.transform, false);
        label.transform.localPosition = new Vector3(0f, 2.7f, 0f);
        markerLabel = label.AddComponent<TextMesh>();
        markerLabel.anchor = TextAnchor.MiddleCenter;
        markerLabel.characterSize = 0.16f;
        markerLabel.fontSize = 48;
        markerLabel.color = new Color(1f, 0.35f, 0.3f, 1f);

        pathLine = GameObject.CreatePrimitive(PrimitiveType.Cube);
        pathLine.name = "CargaMovil_Recorrido";
        Prepare(pathLine, orange);
    }

    private void UpdateVisuals(MovingLoadPath path)
    {
        if (state == null || marker == null) return;
        marker.transform.position = state.worldPoint + Vector3.up * 0.35f;
        if (markerLabel != null)
        {
            markerLabel.text = $"P = {P:0.#} kN";
            Camera cam = Camera.main;
            if (cam != null) markerLabel.transform.rotation = cam.transform.rotation;
        }
        if (pathLine != null)
        {
            Vector3 start = new Vector3(path.origen.x, path.z + 0.33f, path.origen.y);
            Vector3 dir = new Vector3(path.dir[0], 0f, path.dir[1]);
            pathLine.transform.position = start + dir * (path.largo * 0.5f);
            pathLine.transform.rotation = Quaternion.LookRotation(dir, Vector3.up);
            pathLine.transform.localScale = new Vector3(0.08f, 0.08f, path.largo);
        }
    }

    private void LateUpdate()
    {
        if (markerLabel != null && Camera.main != null)
        {
            markerLabel.transform.rotation = Camera.main.transform.rotation;
        }
    }

    private void DestroyVisuals()
    {
        if (marker != null) Destroy(marker);
        if (pathLine != null) Destroy(pathLine);
        marker = null;
        pathLine = null;
        markerLabel = null;
    }

    private void OnDestroy()
    {
        DestroyVisuals();
    }

    private static void Prepare(GameObject obj, Material material)
    {
        obj.GetComponent<Renderer>().material = material;
        Collider col = obj.GetComponent<Collider>();
        if (col != null) Destroy(col);
    }

    private static Material MakeMaterial(Color color)
    {
        Shader shader = Shader.Find("Standard");
        if (shader == null) shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null) shader = Shader.Find("Sprites/Default");
        return new Material(shader) { color = color };
    }

    // ------------------------------------------------------------------
    // Panel (debajo de la consola de capas)
    // ------------------------------------------------------------------
    private void OnGUI()
    {
        if (ViewerUI.Active && ViewerUI.ActiveTab != ViewerUI.TabCargas) return;
        UiTheme.ApplyScale();
        MovingLoadData data = UnityData.GetMovingLoadData();
        if (data == null || data.paths == null || data.paths.Length == 0) return;
        // mientras la carga en elemento esta activa, este panel se oculta
        if (UnityData.ActiveCombo == UnityData.ElementLoadComboName) return;
        // con el modelo modificado (elementos quitados) sus casos unitarios ya no aplican
        if (UnityData.IsModelModified) return;

        Rect left = UiTheme.LeftArea();
        float x = left.x;
        float y = left.yMax + 14f;
        float w = left.width;

        if (!active)
        {
            UiTheme.GUIBox(new Rect(x, y, w, 58f), "CARGA MOVIL (SIDEQUEST)");
            if (GUI.Button(new Rect(x + 10f, y + 28f, w - 20f, 22f), "Activar carga movil P = " + P.ToString("0.#") + " kN"))
            {
                Activate();
            }
            return;
        }

        MovingLoadPath path = CurrentPath();
        float h = Mathf.Max(250f, UiTheme.ScreenH - y - 12f);
        h = Mathf.Min(h, 356f);
        UiTheme.GUIBox(new Rect(x, y, w, h), "CARGA MOVIL (SIDEQUEST)");
        float ix = x + 10f;
        float iw = w - 20f;
        float iy = y + 28f;

        // Recorrido: edificio + piso (eje 2)
        GUI.Label(new Rect(ix, iy, 60f, 20f), "Edificio", UiTheme.DimLabel);
        string[] buildings = BuildingOptions(data);
        int bIndex = System.Array.IndexOf(buildings, path.edificio);
        int nextB = GUI.Toolbar(new Rect(ix + 62f, iy, iw - 62f, 20f), Mathf.Max(0, bIndex), LabelsFor(buildings));
        if (nextB != bIndex)
        {
            SelectPath(data, buildings[nextB], path.nivel);
        }
        iy += 24f;

        GUI.Label(new Rect(ix, iy, 60f, 20f), "Piso", UiTheme.DimLabel);
        string[] floors = FloorOptions(data, CurrentPath().edificio);
        int fIndex = System.Array.IndexOf(floors, CurrentPath().nivel);
        string[] floorLabels = new string[floors.Length];
        for (int i = 0; i < floors.Length; i++) floorLabels[i] = floors[i].Replace("CIELO_", "C");
        int nextF = GUI.Toolbar(new Rect(ix + 62f, iy, iw - 62f, 20f), Mathf.Max(0, fIndex), floorLabels);
        if (nextF != fIndex)
        {
            SelectPath(data, CurrentPath().edificio, floors[nextF]);
        }
        path = CurrentPath();
        iy += 26f;

        // P editable
        GUI.Label(new Rect(ix, iy, 60f, 20f), "P [kN]", UiTheme.DimLabel);
        string nextText = GUI.TextField(new Rect(ix + 60f, iy, 70f, 20f), pText);
        if (nextText != pText)
        {
            pText = nextText;
            if (float.TryParse(pText.Replace(',', '.'), System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out float parsed) && parsed >= 0f)
            {
                P = parsed;
                dirty = true;
            }
        }
        if (GUI.Button(new Rect(ix + 138f, iy, 30f, 20f), "-")) { P = Mathf.Max(0f, P - 10f); pText = P.ToString("0.##"); dirty = true; }
        if (GUI.Button(new Rect(ix + 172f, iy, 30f, 20f), "+")) { P += 10f; pText = P.ToString("0.##"); dirty = true; }
        if (GUI.Button(new Rect(ix + 206f, iy, iw - 206f, 20f), "P = " + data.P_default_kN.ToString("0") + " kN"))
        {
            P = data.P_default_kN; pText = P.ToString("0.##"); dirty = true;
        }
        iy += 26f;

        // Posicion (slider continuo)
        GUI.Label(new Rect(ix, iy, iw, 18f), $"Posicion s = {s:0.00} m  de  L = {path.largo:0.00} m", UiTheme.Label);
        iy += 20f;
        float nextS = GUI.HorizontalSlider(new Rect(ix, iy, iw, 18f), s, 0f, path.largo);
        if (Mathf.Abs(nextS - s) > 1e-4f)
        {
            s = nextS;
            playing = false;
            dirty = true;
        }
        iy += 22f;

        if (GUI.Button(new Rect(ix, iy, 34f, 20f), "|<")) { s = 0f; dirty = true; }
        if (GUI.Button(new Rect(ix + 38f, iy, 74f, 20f), playing ? "Pausa" : "Animar")) { playing = !playing; }
        if (GUI.Button(new Rect(ix + 116f, iy, 34f, 20f), ">|")) { s = path.largo; dirty = true; }
        GUI.Label(new Rect(ix + 158f, iy, 50f, 20f), $"{speed:0.0} m/s", UiTheme.DimLabel);
        speed = GUI.HorizontalSlider(new Rect(ix + 210f, iy + 4f, iw - 210f, 16f), speed, 0.5f, 8f);
        iy += 28f;

        // Lecturas
        if (state != null)
        {
            GUI.Label(new Rect(ix, iy, iw, 18f),
                $"Viga {state.beam.tag}: a = {state.a:0.00} m, b = {state.b:0.00} m (L = {state.L:0.00} m)", UiTheme.Label);
            iy += 18f;
            GUI.Label(new Rect(ix, iy, iw, 18f),
                $"Reparto: F_A = {state.FA:0.00} kN   F_B = {state.FB:0.00} kN", UiTheme.Label);
            iy += 18f;
            float err = Mathf.Abs(state.sumRz - P);
            GUI.Label(new Rect(ix, iy, iw, 18f),
                $"Conservacion: F_A+F_B = {state.FA + state.FB:0.000} kN | Suma Rz apoyos = {state.sumRz:0.000} kN", UiTheme.Label);
            iy += 18f;
            GUI.Label(new Rect(ix, iy, iw, 18f),
                err < 1e-3f * Mathf.Max(1f, P) ? "OK: Suma Rz = P (la carga se conserva)" : $"AVISO: Suma Rz - P = {err:0.000} kN",
                UiTheme.DimLabel);
            iy += 18f;
            GUI.Label(new Rect(ix, iy, iw, 18f),
                $"Momento de empotramiento: M_A = {state.MA:0.0}  M_B = {state.MB:0.0} kN*m", UiTheme.DimLabel);
            iy += 22f;
        }

        if (GUI.Button(new Rect(ix, iy, 96f, 20f), "Momento") && viewer != null) viewer.SetResult("Momento");
        if (GUI.Button(new Rect(ix + 100f, iy, 96f, 20f), "Deformada") && viewer != null) viewer.SetResult("Deformada");
        if (GUI.Button(new Rect(ix + 200f, iy, iw - 200f, 20f), "Cerrar")) Deactivate(true);
    }
}
