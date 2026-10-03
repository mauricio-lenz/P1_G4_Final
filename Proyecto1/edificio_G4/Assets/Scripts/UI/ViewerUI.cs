using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

/// <summary>
/// Interfaz del viewer en UI Toolkit (reemplaza la barra superior, la consola
/// de capas y el panel de resultados IMGUI):
///   - barra superior: caso/combinacion, resultado, camara, busqueda y estado;
///   - dock izquierdo con pestanas VISTA · RESULTADOS · CARGAS · MODIFICAR · ANALISIS;
///   - panel de propiedades del elemento seleccionado (derecha).
/// Los paneles que siguen en IMGUI (carga movil, carga en elemento, quitar
/// elemento) se dibujan dentro de su pestana, en <see cref="HostRect"/>.
/// La agrega StructureViewer en Play.
/// </summary>
public class ViewerUI : MonoBehaviour
{
    public const string TabVista = "VISTA";
    public const string TabResultados = "RESULTADOS";
    public const string TabCargas = "CARGAS";
    public const string TabModificar = "MODIFICAR";
    public const string TabAnalisis = "ANALISIS";
    private static readonly string[] Tabs = { TabVista, TabResultados, TabCargas, TabModificar, TabAnalisis };

    public static bool Active { get; private set; }
    public static string ActiveTab { get; private set; } = TabVista;
    /// Zona (coordenadas GUI) donde la pestana activa aloja paneles IMGUI.
    public static Rect HostRect { get; private set; }
    public static bool TextFocused { get; private set; }

    private static ViewerUI instance;
    /// Parametros editables y reanalisis (persisten aunque se reconstruya la interfaz).
    public static readonly AnalysisSession Session = new AnalysisSession();
    private UIDocument document;
    private VisualElement root;
    private StructureViewer viewer;
    private DiagramController diagrams;
    private ElementPicker picker;

    private readonly Dictionary<string, Button> tabButtons = new Dictionary<string, Button>();
    private readonly Dictionary<string, VisualElement> tabPages = new Dictionary<string, VisualElement>();
    private readonly Dictionary<string, VisualElement> hosts = new Dictionary<string, VisualElement>();
    private VisualElement tabBody;
    private readonly Dictionary<string, Button> caseButtons = new Dictionary<string, Button>();
    private readonly Dictionary<string, Button> resultButtons = new Dictionary<string, Button>();
    private readonly List<System.Action> syncers = new List<System.Action>();
    private Label statusLabel;
    private VisualElement propsPanel;
    private Label propsTitle;
    private VisualElement propsBody;
    private string propsText;
    private float nextSync;

    private static readonly (string name, string label)[] ResultModes =
    {
        ("None", "Sin diagrama"), ("Axial", "Axial N"), ("Corte", "Corte V"), ("Momento", "Momento M"), ("Deformada", "Deformada"),
    };

    // ------------------------------------------------------------------
    private void Start()
    {
        viewer = GetComponent<StructureViewer>();
        diagrams = viewer.Diagrams;
        picker = FindAnyObjectByType<ElementPicker>();
        Session.LoadFrom(viewer.Data);   // antes de construir: la pestana ANALISIS muestra estos valores
        if (!Build())
        {
            Debug.LogWarning("[ViewerUI] No se pudo crear la interfaz UI Toolkit; se usa la interfaz IMGUI.");
            return;
        }
        instance = this;
        Active = true;
        viewer.ModelReloaded += Rebuild;
        SelectTab(ActiveTab);
        SyncAll();
    }

    /// Tras recargar el modelo (reanalisis): se rehace la interfaz con los datos nuevos.
    private void Rebuild()
    {
        diagrams = viewer.Diagrams;
        root.Clear();
        tabButtons.Clear(); tabPages.Clear(); hosts.Clear(); caseButtons.Clear(); resultButtons.Clear(); syncers.Clear();
        propsText = null;
        BuildTopBar();
        BuildDock();
        BuildProps();
        SelectTab(ActiveTab);
        SyncAll();
    }

    private void OnDestroy()
    {
        if (instance == this) { Active = false; instance = null; HostRect = Rect.zero; }
        if (viewer != null) viewer.ModelReloaded -= Rebuild;
        if (document != null) Destroy(document.gameObject);
    }

    private bool Build()
    {
        var theme = Resources.Load<ThemeStyleSheet>("UI/ViewerTheme");
        var sheet = Resources.Load<StyleSheet>("UI/viewer");
        if (theme == null || sheet == null) return false;

        var settings = ScriptableObject.CreateInstance<PanelSettings>();
        settings.name = "ViewerPanelSettings";
        settings.themeStyleSheet = theme;
        if (Application.isMobilePlatform)
        {
            // mismas unidades que la GUI IMGUI del celular (pantalla virtual de 720 de alto)
            settings.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            settings.referenceResolution = new Vector2Int(1280, 720);
            settings.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
            settings.match = 1f;
        }
        else
        {
            settings.scaleMode = PanelScaleMode.ConstantPixelSize;
            settings.scale = 1f;
        }

        var go = new GameObject("ViewerUI (UI Toolkit)");
        document = go.AddComponent<UIDocument>();
        document.panelSettings = settings;
        root = document.rootVisualElement;
        root.styleSheets.Add(sheet);
        root.AddToClassList("root");
        root.pickingMode = PickingMode.Ignore;

        BuildTopBar();
        BuildDock();
        BuildProps();
        return true;
    }

    // ------------------------------------------------------------------
    // Barra superior
    // ------------------------------------------------------------------
    private void BuildTopBar()
    {
        var bar = Panel("topbar");
        root.Add(bar);

        var row1 = Row();
        row1.Add(Text("GRUPO 4 · P1_G4", "brand"));
        row1.Add(Text("Modelo OpenSees · edificios 1 y 2 · G35 / A36", "brand-sub"));
        row1.Add(Spacer());
        var search = Input(new TextField { value = "" });
        search.AddToClassList("search");
        search.tooltip = "Id o elementTag (ej. E1_72)";
        search.RegisterCallback<FocusInEvent>(_ => TextFocused = true);
        search.RegisterCallback<FocusOutEvent>(_ => TextFocused = false);
        search.RegisterCallback<KeyDownEvent>(e =>
        {
            if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) viewer.Search(search.value);
        });
        row1.Add(search);
        row1.Add(Btn("Buscar", () => viewer.Search(search.value), "small"));
        row1.Add(Gap());
        var cams = Seg();
        foreach (string p in new[] { "ISO", "TOP", "FRONT", "RIGHT" })
        {
            string preset = p;
            cams.Add(Btn(p, () => viewer.CameraPreset(preset), "small"));
        }
        FinishSeg(cams);
        row1.Add(cams);
        bar.Add(row1);

        var row2 = Row();
        row2.Add(Text("Caso", "group-label", "first"));
        var cases = Seg();
        var names = new List<string> { "G", "Q", "EX", "EY" };
        foreach (string c in viewer.ComboNames) if (!names.Contains(c) && c != "G (sin combo)") names.Add(c);
        foreach (string c in names)
        {
            string name = c;
            Button b = Btn(name, () => viewer.SetCase(name), "small");
            b.tooltip = UnityData.GetComboLabel(name);
            caseButtons[name] = b;
            cases.Add(b);
        }
        FinishSeg(cases);
        row2.Add(cases);
        row2.Add(Text("Resultado", "group-label"));
        var results = Seg();
        foreach (var (name, label) in ResultModes)
        {
            string n = name;
            Button b = Btn(label, () => viewer.SetResult(n), "small");
            resultButtons[name] = b;
            results.Add(b);
        }
        FinishSeg(results);
        row2.Add(results);
        bar.Add(row2);

        statusLabel = Text("", "status");
        bar.Add(statusLabel);

        syncers.Add(() =>
        {
            string active = UnityData.ActiveCombo;
            foreach (var kv in caseButtons) kv.Value.EnableInClassList("on", kv.Key == active);
            string mode = diagrams != null ? diagrams.CurrentResultName() : "None";
            foreach (var kv in resultButtons) kv.Value.EnableInClassList("on", kv.Key == mode);
            string hint = Application.isMobilePlatform
                ? "Toque: seleccionar · 1 dedo: orbitar · pellizco: zoom · 2 dedos: desplazar"
                : "Clic: seleccionar · clic der.: orbitar · rueda: zoom · 1-4: diagramas · +/−: escala";
            string sup = active == UnityData.SuperpositionComboName ? "  ·  SUP = " + UnityData.GetComboLabel(active) : "";
            statusLabel.text = (viewer.Status ?? "") + sup + "     |     " + hint;
        });
    }

    // ------------------------------------------------------------------
    // Dock con pestanas
    // ------------------------------------------------------------------
    private void BuildDock()
    {
        var dock = Panel("dock");
        dock.style.flexDirection = FlexDirection.Column;
        dock.pickingMode = PickingMode.Ignore;
        root.Add(dock);

        var tabs = new VisualElement();
        tabs.AddToClassList("tabs");
        foreach (string t in Tabs)
        {
            string tab = t;
            var b = new Button(() => SelectTab(tab)) { text = tab == TabAnalisis ? "ANÁLISIS" : tab };
            b.AddToClassList("tab");
            tabButtons[tab] = b;
            tabs.Add(b);
        }
        dock.Add(tabs);

        tabBody = new VisualElement();
        tabBody.AddToClassList("tab-body");
        dock.Add(tabBody);

        tabPages[TabVista] = Page(BuildVista);
        tabPages[TabResultados] = Page(BuildResultados);
        tabPages[TabCargas] = HostPage(TabCargas,
            "Carga móvil sobre un recorrido de vigas y carga puntual o repartida en un elemento. " +
            "Ambas se resuelven con superposición de casos unitarios de OpenSees.");
        tabPages[TabModificar] = HostPage(TabModificar,
            "Quitar elementos y reanalizar con OpenSees en segundo plano. El resultado se compara con el modelo original.");
        tabPages[TabAnalisis] = Page(BuildAnalisis);
        foreach (var page in tabPages.Values) tabBody.Add(page);
    }

    public static void ShowTab(string tab)
    {
        if (instance != null) instance.SelectTab(tab);
    }

    private void SelectTab(string tab)
    {
        ActiveTab = tab;
        foreach (var kv in tabButtons) kv.Value.EnableInClassList("on", kv.Key == tab);
        foreach (var kv in tabPages) kv.Value.style.display = kv.Key == tab ? DisplayStyle.Flex : DisplayStyle.None;
        // las pestanas con paneles IMGUI dejan transparente el cuerpo para que se vean encima
        tabBody.EnableInClassList("host-mode", hosts.ContainsKey(tab));
    }

    private VisualElement Page(System.Action<VisualElement> fill)
    {
        var scroll = new ScrollView(ScrollViewMode.Vertical);
        scroll.AddToClassList("tab-scroll");
        var content = new VisualElement();
        content.AddToClassList("tab-content");
        fill(content);
        scroll.Add(content);
        return scroll;
    }

    private VisualElement HostPage(string tab, string hint)
    {
        var page = new VisualElement();
        page.style.flexGrow = 1;
        var head = new VisualElement();
        head.AddToClassList("tab-content");
        head.style.backgroundColor = new Color(0.035f, 0.05f, 0.094f, 0.95f);
        head.style.paddingBottom = 8;
        var h = Text(hint, "hint");
        h.style.marginBottom = 0;
        head.Add(h);
        if (!PythonJob.Available && tab == TabModificar)
        {
            head.Add(Text("Requiere Python + OpenSees en el PC (no disponible en este equipo).", "hint"));
        }
        if (tab == TabModificar)
        {
            // editores en un contenedor desplazable: el panel IMGUI de quitar elemento queda debajo
            var editors = new ScrollView(ScrollViewMode.Vertical);
            editors.style.maxHeight = 470;
            BuildArmaduraEditor(editors);
            BuildSectionEditor(editors);
            head.Add(editors);
        }
        page.Add(head);
        var host = new VisualElement();
        host.AddToClassList("host");
        page.Add(host);
        hosts[tab] = host;
        return page;
    }

    // ---- VISTA ----
    private void BuildVista(VisualElement c)
    {
        c.Add(Title("CAPAS", true));
        var grid = new VisualElement();
        grid.AddToClassList("grid3");
        grid.Add(Check("Columnas", () => viewer.ShowColumnsLayer, v => viewer.ShowColumnsLayer = v));
        grid.Add(Check("Vigas", () => viewer.ShowBeamsLayer, v => viewer.ShowBeamsLayer = v));
        grid.Add(Check("Muros", () => viewer.ShowWallsLayer, v => viewer.ShowWallsLayer = v));
        grid.Add(Check("Apoyos", () => viewer.ShowSupportsLayer, v => viewer.ShowSupportsLayer = v));
        grid.Add(Check("Losas", () => viewer.ShowSlabsLayer, v => viewer.ShowSlabsLayer = v));
        grid.Add(Check("Nodos", () => viewer.ShowNodesLayer, v => viewer.ShowNodesLayer = v));
        grid.Add(Check("IDs", () => viewer.ShowIdsLayer, v => viewer.ShowIdsLayer = v));
        grid.Add(Check("Ejes locales", () => viewer.ShowLocalAxesLayer, v => viewer.ShowLocalAxesLayer = v));
        grid.Add(Check("Cargas", () => viewer.ShowLoadsLayer, v => viewer.ShowLoadsLayer = v));
        c.Add(grid);

        var presets = Row();
        presets.style.marginTop = 6;
        presets.Add(Btn("Mostrar todo", () => viewer.ShowAllLayers(), "wide"));
        presets.Add(Btn("Solo estructura", () => viewer.StructureOnly(), "wide"));
        c.Add(presets);

        c.Add(Title("PISO"));
        var floors = new DropdownField(new List<string>(viewer.FloorNames), viewer.FloorIndex);
        floors.AddToClassList("dropdown");
        floors.RegisterValueChangedCallback(e =>
        {
            viewer.FloorIndex = floors.index;
            viewer.Status = "Filtro de piso: " + e.newValue;
        });
        syncers.Add(() => { if (floors.index != viewer.FloorIndex) floors.SetValueWithoutNotify(viewer.FloorNames[viewer.FloorIndex]); });
        c.Add(floors);

        c.Add(Title("ÁREAS TRIBUTARIAS POR PISO"));
        if (viewer.TributaryFloors.Count == 0) c.Add(Text("Sin resumen tributario en el JSON.", "hint"));
        foreach (var kv in viewer.TributaryFloors)
        {
            c.Add(KeyValue(kv.Key, $"{kv.Value.area_total:0.0} m²  ·  {kv.Value.carga_total:0} kN"));
        }
    }

    // ---- RESULTADOS ----
    private void BuildResultados(VisualElement c)
    {
        c.Add(Title("DIAGRAMA", true));
        c.Add(Text("Plano de flexión (ejes locales del elemento)", "hint"));
        var planes = Seg();
        var planeButtons = new List<Button>();
        string[] planeLabels = { "Auto", "xz · My, Vz", "xy · Mz, Vy" };
        for (int i = 0; i < 3; i++)
        {
            int idx = i;
            Button b = Btn(planeLabels[i], () => { DiagramController.DiagramPlane = (DiagramController.Plane)idx; RefreshDiagrams(); }, "small", "wide");
            planeButtons.Add(b);
            planes.Add(b);
        }
        FinishSeg(planes);
        c.Add(planes);
        syncers.Add(() => { for (int i = 0; i < 3; i++) planeButtons[i].EnableInClassList("on", (int)DiagramController.DiagramPlane == i); });

        var types = Row();
        types.style.marginTop = 6;
        types.Add(Check("Vigas", () => DiagramController.ShowBeams, v => { DiagramController.ShowBeams = v; RefreshDiagrams(); }));
        types.Add(Check("Columnas y arriostres", () => DiagramController.ShowColumns, v => { DiagramController.ShowColumns = v; RefreshDiagrams(); }));
        c.Add(types);

        // escala logaritmica: 0..1 -> x0.1 .. x10
        var scaleRow = new VisualElement();
        scaleRow.AddToClassList("slider-row");
        scaleRow.Add(new Label("Escala"));
        var scale = new Slider(0f, 1f) { value = ScaleToSlider(DiagramController.DiagramScale) };
        scale.AddToClassList("slider");
        var scaleNum = Text("", "num");
        scale.RegisterValueChangedCallback(e =>
        {
            DiagramController.DiagramScale = Mathf.Pow(10f, 2f * e.newValue - 1f);
            scaleNum.text = "x" + DiagramController.DiagramScale.ToString("0.00");
        });
        scale.RegisterCallback<PointerCaptureOutEvent>(_ => RefreshDiagrams());
        scaleRow.Add(scale);
        scaleRow.Add(scaleNum);
        c.Add(scaleRow);
        syncers.Add(() =>
        {
            float s = ScaleToSlider(DiagramController.DiagramScale);
            if (Mathf.Abs(scale.value - s) > 0.002f && scale.panel?.GetCapturingElement(PointerId.mousePointerId) != scale) scale.SetValueWithoutNotify(s);
            scaleNum.text = "x" + DiagramController.DiagramScale.ToString("0.00");
        });

        var labels = new DropdownField("Etiquetas", new List<string> { "No", "Máximos", "Seleccionado" },
            (int)DiagramController.Labels);
        labels.AddToClassList("dropdown");
        labels.RegisterValueChangedCallback(_ => DiagramController.Labels = (DiagramController.LabelMode)labels.index);
        c.Add(labels);
        c.Add(Check("Animar la deformada", () => DiagramController.AnimateDeformed, v => DiagramController.AnimateDeformed = v));

        c.Add(Title("CONVENCIÓN"));
        c.Add(Legend(new Color(0.45f, 0.78f, 1f), "M+ (tracción abajo) · N tracción · V+"));
        c.Add(Legend(new Color(1f, 0.70f, 0.36f), "M− (tracción arriba) · N compresión · V−"));
        c.Add(Text("El momento se dibuja del lado traccionado. Escala común a todo el modelo: el tamaño compara barras entre sí. " +
                   "Pasa el mouse sobre un diagrama para leer x y el valor.", "hint"));

        c.Add(Title("COLOREAR POR UTILIZACIÓN"));
        c.Add(Check("Demanda / capacidad P-M (C)", () => viewer.UtilizationColors, v =>
        {
            viewer.SetUtilizationVisible(v);
            viewer.Status = v ? "Colores por C = demanda/capacidad P-M." : "Colores por capa restaurados.";
        }));
        c.Add(Legend(new Color(0.25f, 0.8f, 0.35f), "C ≤ 0,7"));
        c.Add(Legend(new Color(1f, 0.85f, 0.2f), "C ≈ 1"));
        c.Add(Legend(new Color(1f, 0.3f, 0.25f), "C > 1"));

        c.Add(Title("SUPERPOSICIÓN EN VIVO"));
        c.Add(Text("SUP = λG·G + λQ·Q + λEX·EX + λEY·EY, sin reanalizar (análisis lineal).", "hint"));
        float[] lam = viewer.SuperpositionValues;
        var sliders = new Slider[4];
        string[] names = { "λG", "λQ", "λEX", "λEY" };
        var supToggle = new Toggle("Activar superposición") { value = viewer.SuperpositionActive };
        supToggle.AddToClassList("chk");
        System.Action apply = () => viewer.SetSuperposition(supToggle.value, sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value);
        supToggle.RegisterValueChangedCallback(_ => apply());
        c.Add(supToggle);
        for (int i = 0; i < 4; i++)
        {
            var row = new VisualElement();
            row.AddToClassList("slider-row");
            row.Add(new Label(names[i]));
            var s = new Slider(-3f, 4f) { value = lam[i] };
            s.AddToClassList("slider");
            var num = Text(lam[i].ToString("0.00"), "num");
            s.RegisterValueChangedCallback(e => { num.text = e.newValue.ToString("0.00"); if (supToggle.value) apply(); });
            sliders[i] = s;
            row.Add(s);
            row.Add(num);
            c.Add(row);
        }
        var supButtons = Row();
        supButtons.Add(Btn("λ = 1", () => { foreach (var s in sliders) s.value = 1f; }, "wide"));
        supButtons.Add(Btn("Solo G", () => { sliders[0].value = 1f; sliders[1].value = 0f; sliders[2].value = 0f; sliders[3].value = 0f; }, "wide"));
        c.Add(supButtons);
        syncers.Add(() => { if (supToggle.value != viewer.SuperpositionActive) supToggle.SetValueWithoutNotify(viewer.SuperpositionActive); });
    }

    private static float ScaleToSlider(float scale) => (Mathf.Log10(Mathf.Clamp(scale, 0.1f, 10f)) + 1f) / 2f;

    private void RefreshDiagrams()
    {
        if (diagrams != null) diagrams.Refresh();
    }

    // ---- MODIFICAR: armadura del elemento seleccionado ----
    private void BuildArmaduraEditor(VisualElement c)
    {
        c.Add(Title("ARMADURA (ACI 318)", true));
        var info = Text("Selecciona una viga o columna de hormigón.", "hint");
        c.Add(info);
        var estado = Text("", "line");
        c.Add(estado);

        // campos: vigas (5) y columnas (2); se muestran segun el tipo
        string[] beamKeys = { "Inferior", "Superior", "Suple apoyo", "Estribos apoyo", "Estribos tramo" };
        string[] colKeys = { "Barras", "Estribos" };
        var beamFields = new List<TextField>();
        var colFields = new List<TextField>();
        var beamBox = new VisualElement();
        var colBox = new VisualElement();
        foreach (string k in beamKeys) { var f = ArmField(k); beamFields.Add(f); beamBox.Add(f); }
        foreach (string k in colKeys) { var f = ArmField(k); colFields.Add(f); colBox.Add(f); }
        c.Add(beamBox);
        c.Add(colBox);
        c.Add(Text("Notación: 4f22 o 4φ22, 2f22+2f25; estribos Ef10a10 (2 ramas), EDf10a10 (doble, 4 ramas).", "hint"));

        var row1 = Row();
        var toElem = Btn("Aplicar al elemento", null, "wide");
        var toSec = Btn("Aplicar a la sección", null, "wide");
        row1.Add(toElem);
        row1.Add(toSec);
        c.Add(row1);
        var row2 = Row();
        var clear = Btn("Quitar cambios", null, "wide");
        var run = Btn("Reanalizar ahora", () => { if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso..."; }, "wide");
        row2.Add(clear);
        row2.Add(run);
        c.Add(row2);
        var pending = Text("", "hint");
        c.Add(pending);

        ElementData current = null;
        System.Func<AnalysisSession.Arm> read = () =>
        {
            var a = new AnalysisSession.Arm();
            if (current == null) return a;
            ArmaduraData now = current.capacidad != null ? current.capacidad.armadura : null;
            string Pick(TextField f, string old) => string.IsNullOrWhiteSpace(f.value) || f.value.Trim() == (old ?? "") ? null : f.value.Trim();
            if (current.type == "viga")
            {
                a.inferior = Pick(beamFields[0], now?.inferior);
                a.superior = Pick(beamFields[1], now?.superior);
                a.supleApoyo = Pick(beamFields[2], now?.supleApoyo);
                a.estribosApoyo = Pick(beamFields[3], now?.estribosApoyo);
                a.estribosTramo = Pick(beamFields[4], now?.estribosTramo);
            }
            else
            {
                a.barras = Pick(colFields[0], now?.barras);
                a.estribos = Pick(colFields[1], now?.estribos);
            }
            return a;
        };
        System.Action fill = () =>
        {
            ArmaduraData now = current != null && current.capacidad != null ? current.capacidad.armadura : null;
            AnalysisSession.Arm pendingElem = current != null && Session.armElem.TryGetValue(current.elementTag, out var pe) ? pe : null;
            AnalysisSession.Arm pendingSec = current != null && Session.armSec.TryGetValue(current.sectionId ?? "", out var ps) ? ps : null;
            string V(string elem, string sec, string cur) => elem ?? sec ?? cur ?? "";
            beamFields[0].SetValueWithoutNotify(V(pendingElem?.inferior, pendingSec?.inferior, now?.inferior));
            beamFields[1].SetValueWithoutNotify(V(pendingElem?.superior, pendingSec?.superior, now?.superior));
            beamFields[2].SetValueWithoutNotify(V(pendingElem?.supleApoyo, pendingSec?.supleApoyo, now?.supleApoyo));
            beamFields[3].SetValueWithoutNotify(V(pendingElem?.estribosApoyo, pendingSec?.estribosApoyo, now?.estribosApoyo));
            beamFields[4].SetValueWithoutNotify(V(pendingElem?.estribosTramo, pendingSec?.estribosTramo, now?.estribosTramo));
            colFields[0].SetValueWithoutNotify(V(pendingElem?.barras, pendingSec?.barras, now?.barras));
            colFields[1].SetValueWithoutNotify(V(pendingElem?.estribos, pendingSec?.estribos, now?.estribos));
        };
        toElem.clicked += () =>
        {
            if (current == null) return;
            AnalysisSession.Arm a = read();
            if (a.Describe().Length == 0) { viewer.Status = "Sin cambios de armadura."; return; }
            Session.armElem[current.elementTag] = a;
            viewer.Status = $"Armadura de {current.elementTag}: {a.Describe()}. Reanaliza para ver el factor de uso.";
        };
        toSec.clicked += () =>
        {
            if (current == null) return;
            AnalysisSession.Arm a = read();
            if (a.Describe().Length == 0) { viewer.Status = "Sin cambios de armadura."; return; }
            Session.armSec[current.sectionId] = a;
            viewer.Status = $"Armadura tipo de {current.sectionId}: {a.Describe()}. Reanaliza para ver el factor de uso.";
        };
        clear.clicked += () =>
        {
            if (current == null) return;
            Session.armElem.Remove(current.elementTag);
            Session.armSec.Remove(current.sectionId ?? "");
            fill();
        };

        syncers.Add(() =>
        {
            ElementData e = picker != null && picker.Selected != null ? picker.Selected.data : null;
            bool editable = e != null && e.capacidad != null && e.capacidad.armadura != null && (e.type == "viga" || e.type == "columna");
            ElementData next = editable ? e : null;
            if (next != current)
            {
                current = next;
                fill();
            }
            beamBox.style.display = current != null && current.type == "viga" ? DisplayStyle.Flex : DisplayStyle.None;
            colBox.style.display = current != null && current.type == "columna" ? DisplayStyle.Flex : DisplayStyle.None;
            info.text = current != null ? $"{current.elementTag} · {current.type} {current.sectionId}"
                : e != null ? $"{e.elementTag}: sin armadura de hormigón editable" : "Selecciona una viga o columna de hormigón.";
            if (current != null)
            {
                CapacityData cap = current.capacidad;
                CapacityCombo cc = cap.ForCombo(UnityData.ActiveCombo);
                float dcr = cc != null ? Mathf.Max(cc.DCR_flexion, Mathf.Max(cc.DCR_corte, cc.DCR_PM)) : cap.DCR;
                string semaforo = dcr > 1f ? "NO CUMPLE" : dcr > 0.9f ? "al límite" : "cumple";
                estado.text = current.type == "viga"
                    ? $"φMn+ {cap.phiMn_pos_kN_m:0} · φMn− {cap.phiMn_neg_kN_m:0} kN·m · φVn {cap.phiVn_apoyo_kN:0} kN · DCR {dcr:0.00} ({semaforo})"
                    : $"φPmax {cap.phiPmax_kN:0} kN · Ast {cap.Ast_mm2:0} mm² · DCR {dcr:0.00} ({semaforo})";
                estado.style.color = dcr > 1f ? new Color(1f, 0.45f, 0.35f) : dcr > 0.9f ? new Color(1f, 0.8f, 0.3f) : new Color(0.55f, 0.9f, 0.6f);
            }
            else estado.text = "";
            toElem.SetEnabled(current != null && !Session.job.Running);
            toSec.SetEnabled(current != null && !Session.job.Running);
            clear.SetEnabled(current != null);
            run.SetEnabled(PythonJob.Available && !Session.job.Running);
            run.text = Session.job.Running ? $"Analizando... {Session.job.Elapsed:0} s" : "Reanalizar ahora";
            var lines = new List<string>();
            foreach (var kv in Session.armSec) lines.Add($"Sección {kv.Key}: {kv.Value.Describe()}");
            foreach (var kv in Session.armElem) lines.Add($"{kv.Key}: {kv.Value.Describe()}");
            pending.text = lines.Count == 0 ? "Sin cambios de armadura pendientes." : "Pendientes:\n" + string.Join("\n", lines);
        });
    }

    private TextField ArmField(string label)
    {
        var f = Input(new TextField(label) { value = "" });
        f.AddToClassList("dropdown");
        f.RegisterCallback<FocusInEvent>(_ => TextFocused = true);
        f.RegisterCallback<FocusOutEvent>(_ => TextFocused = false);
        return f;
    }

    // ---- MODIFICAR: cambio de seccion ----
    private void BuildSectionEditor(VisualElement c)
    {
        c.Add(Title("CAMBIAR SECCIÓN"));
        var info = Text("Selecciona una viga o columna de hormigón.", "hint");
        c.Add(info);

        // secciones rectangulares de hormigon del modelo (las de acero y muros equivalentes no se editan aqui)
        var presets = new SortedDictionary<string, Vector2>();
        foreach (ElementData e in viewer.Data.elements)
        {
            string sid = e.sectionId ?? "";
            if ((sid.StartsWith("V") && !sid.StartsWith("VM")) || sid.StartsWith("COL")) presets[sid] = new Vector2(e.width_m, e.height_m);
        }
        var choices = new List<string>(presets.Keys);
        var preset = new DropdownField("Sección", choices, 0);
        preset.AddToClassList("dropdown");
        var bField = Input(new FloatField("b [m]") { value = 0.6f, formatString = "0.###" });
        var hField = Input(new FloatField("h [m]") { value = 0.8f, formatString = "0.###" });
        bField.AddToClassList("dropdown");
        hField.AddToClassList("dropdown");
        preset.RegisterValueChangedCallback(e =>
        {
            if (presets.TryGetValue(e.newValue, out Vector2 d)) { bField.SetValueWithoutNotify(d.x); hField.SetValueWithoutNotify(d.y); }
        });
        c.Add(preset);
        var dims = Row();
        dims.Add(bField);
        dims.Add(hField);
        c.Add(dims);
        var buttons = Row();
        var add = Btn("Agregar cambio", null, "wide");
        var undo = Btn("Quitar cambio", null, "wide");
        buttons.Add(add);
        buttons.Add(undo);
        c.Add(buttons);
        var list = new VisualElement();
        c.Add(list);
        c.Add(Text("Los cambios se aplican con Reanalizar (pestaña ANÁLISIS); el peso propio se recalcula con la nueva sección.", "hint"));

        ElementData current = null;
        System.Action refreshList = () =>
        {
            list.Clear();
            foreach (var sc in Session.sections.Values)
                list.Add(KeyValue(sc.tag, $"{sc.before} → {sc.sectionId} ({sc.width:0.00} x {sc.height:0.00} m)"));
        };
        add.clicked += () =>
        {
            if (current == null) return;
            string sid = $"{(current.type == "columna" ? "COL" : "V")}{Mathf.RoundToInt(bField.value * 100)}/{Mathf.RoundToInt(hField.value * 100)}";
            string before = Session.sections.TryGetValue(current.id, out var prev) ? prev.before : current.sectionId;
            Session.SetSection(current, sid, bField.value, hField.value, before);
            viewer.Status = $"Cambio de sección pendiente: {current.elementTag} {before} → {sid}. Reanaliza en ANÁLISIS.";
            refreshList();
        };
        undo.clicked += () =>
        {
            if (current == null) return;
            Session.sections.Remove(current.id);
            refreshList();
        };
        refreshList();
        syncers.Add(() =>
        {
            ElementData e = picker != null && picker.Selected != null ? picker.Selected.data : null;
            bool editable = e != null && (e.type == "viga" || e.type == "columna") && presets.ContainsKey(e.sectionId ?? "");
            if (e != current)
            {
                current = editable ? e : null;
                if (current != null)
                {
                    preset.SetValueWithoutNotify(current.sectionId);
                    bField.SetValueWithoutNotify(current.width_m);
                    hField.SetValueWithoutNotify(current.height_m);
                }
            }
            info.text = current != null ? $"{current.elementTag} · {current.type} · sección actual {current.sectionId}"
                : e != null ? $"{e.elementTag}: sección {e.sectionId} (no editable aquí)" : "Selecciona una viga o columna de hormigón.";
            add.SetEnabled(current != null && !Session.job.Running);
            undo.SetEnabled(current != null && Session.sections.ContainsKey(current.id));
            if (list.childCount != Session.sections.Count) refreshList();
        });
    }

    // ---- ANALISIS: parametros, combinaciones y reanalisis ----
    private void BuildAnalisis(VisualElement c)
    {
        StructureData d = viewer.Data;
        c.Add(Title("MODELO", true));
        if (d != null)
        {
            int beams = 0, cols = 0, braces = 0, walls = 0, links = 0;
            foreach (ElementData e in d.elements)
            {
                if (e.type == "viga") beams++; else if (e.type == "columna") cols++; else if (e.type == "muro") walls++;
                else if (e.type == "rigido") links++; else braces++;
            }
            c.Add(KeyValue("Nodos · elementos", $"{d.nodes.Length} · {beams + cols + braces} ({beams} V, {cols} C, {braces} A)"));
            if (walls > 0) c.Add(KeyValue("Muros en el análisis", $"{walls} paños (columna ancha) · {links} brazos rígidos"));
            c.Add(KeyValue("Muros · apoyos", $"{d.walls?.Length ?? 0} · {d.supports?.Length ?? 0}"));
            c.Add(KeyValue("Resultados cargados", viewer.LoadedSource));
        }

        c.Add(Title("PARÁMETROS DE CARGA"));
        var qG = Input(new FloatField("q_G losa + terminaciones [kN/m²]") { value = Session.qG, formatString = "0.###" });
        var qQ = Input(new FloatField("Q sobrecarga de uso [kg/m²]") { value = Session.qKgM2, formatString = "0.###" });
        var sc = Input(new FloatField("Coeficiente sísmico C") { value = Session.seismicCoeff, formatString = "0.###" });
        foreach (var f in new[] { qG, qQ, sc })
        {
            f.AddToClassList("dropdown");
            c.Add(f);
        }
        qG.RegisterValueChangedCallback(e => Session.qG = Mathf.Max(0f, e.newValue));
        qQ.RegisterValueChangedCallback(e => Session.qKgM2 = Mathf.Max(0f, e.newValue));
        sc.RegisterValueChangedCallback(e => Session.seismicCoeff = Mathf.Max(0f, e.newValue));
        c.Add(Text("G = q_G·A_trib + peso propio (25 kN/m³ hormigón, 78,5 kN/m³ acero). Sismo: C·(D + 0,5Q) por piso.", "hint"));

        c.Add(Title("RIGIDEZ (FACTOR SOBRE LA INERCIA BRUTA)"));
        var kv = Input(new FloatField("Vigas") { value = Session.kViga, formatString = "0.###" });
        var kc = Input(new FloatField("Columnas") { value = Session.kColumna, formatString = "0.###" });
        var km = Input(new FloatField("Muros") { value = Session.kMuro, formatString = "0.###" });
        foreach (var f in new[] { kv, kc, km }) { f.AddToClassList("dropdown"); c.Add(f); }
        kv.RegisterValueChangedCallback(e => Session.kViga = Mathf.Clamp(e.newValue, 0.05f, 1f));
        kc.RegisterValueChangedCallback(e => Session.kColumna = Mathf.Clamp(e.newValue, 0.05f, 1f));
        km.RegisterValueChangedCallback(e => Session.kMuro = Mathf.Clamp(e.newValue, 0.05f, 1f));
        var kRow = Row();
        kRow.Add(Btn("ACI fisurada", () => { kv.value = 0.35f; kc.value = 0.70f; km.value = 0.35f; }, "wide"));
        kRow.Add(Btn("Sección bruta", () => { kv.value = 1f; kc.value = 1f; km.value = 1f; }, "wide"));
        c.Add(kRow);
        c.Add(Text("ACI 318-19 §6.6.3.1.1: vigas 0,35, columnas 0,70, muros fisurados 0,35 (no fisurados 0,70). Acero sin reducción.", "hint"));

        c.Add(Title("COMBINACIONES  ·  λG  λQ  λEX  λEY"));
        var comboList = new VisualElement();
        c.Add(comboList);
        System.Action buildCombos = null;
        buildCombos = () =>
        {
            comboList.Clear();
            foreach (AnalysisSession.Combo combo in Session.combos)
            {
                AnalysisSession.Combo cb = combo;
                var row = Row();
                row.style.marginBottom = 3;
                var name = Input(new TextField { value = cb.name });
                name.AddToClassList("search");
                name.style.width = 48;
                name.RegisterCallback<FocusInEvent>(_ => TextFocused = true);
                name.RegisterCallback<FocusOutEvent>(_ => TextFocused = false);
                name.RegisterValueChangedCallback(e => cb.name = e.newValue.Trim());
                row.Add(name);
                row.Add(Factor(cb.G, v => cb.G = v));
                row.Add(Factor(cb.Q, v => cb.Q = v));
                row.Add(Factor(cb.EX, v => cb.EX = v));
                row.Add(Factor(cb.EY, v => cb.EY = v));
                row.Add(Btn("✕", () => { Session.combos.Remove(cb); buildCombos(); }, "small"));
                comboList.Add(row);
            }
        };
        buildCombos();
        c.Add(Btn("+ Agregar combinación", () =>
        {
            Session.combos.Add(new AnalysisSession.Combo { name = "C" + (Session.combos.Count + 1), G = 1f, Q = 0.5f });
            buildCombos();
        }, "wide"));

        c.Add(Title("CAMBIOS DE SECCIÓN Y ARMADURA"));
        var secs = Text("", "hint");
        c.Add(secs);

        c.Add(Title("REANÁLISIS CON OPENSEES"));
        var run = Btn("Reanalizar el modelo completo", () =>
        {
            if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso...";
        }, "wide");
        run.style.height = 30;
        c.Add(run);
        var reset = Btn("Restaurar valores del modelo cargado", () => { Session.LoadFrom(viewer.Data); Rebuild(); }, "wide");
        c.Add(reset);
        var progress = Text("", "hint");
        c.Add(progress);
        syncers.Add(() =>
        {
            bool running = Session.job.Running;
            run.SetEnabled(PythonJob.Available && !running);
            reset.SetEnabled(!running);
            run.text = running ? $"Analizando...  {Session.job.Elapsed:0} s" : "Reanalizar el modelo completo";
            progress.text = running ? (Session.job.LastLine ?? "") : Session.Message;
            var lines = new List<string>();
            foreach (var x in Session.sections.Values) lines.Add($"{x.tag}: {x.before} → {x.sectionId}");
            foreach (var kv in Session.armSec) lines.Add($"Armadura {kv.Key}: {kv.Value.Describe()}");
            foreach (var kv in Session.armElem) lines.Add($"Armadura {kv.Key}: {kv.Value.Describe()}");
            secs.text = lines.Count == 0 ? "Sin cambios (se agregan en la pestaña MODIFICAR)." : string.Join("\n", lines);
        });
        if (!PythonJob.Available) c.Add(Text("Requiere Python + OpenSees en este equipo (carpeta Proyecto1/scripts).", "hint"));

        // verificacion del analisis cargado
        AnalysisSummary r = d?.resumenAnalisis;
        c.Add(Title("VERIFICACIÓN DEL ANÁLISIS CARGADO"));
        if (r == null || r.G_aplicada_kN == 0f)
        {
            c.Add(Text("El JSON cargado no trae resumen (se genera al reanalizar o al exportar de nuevo).", "hint"));
        }
        else
        {
            c.Add(KeyValue("q_G · Q · C", $"{r.q_G_kN_m2:0.00} kN/m² · {r.Q_kN_m2:0.00} kN/m² · {r.coeficienteSismico:0.###}"));
            c.Add(KeyValue("Rigidez V · C · M", $"{r.rigidezViga:0.##} · {r.rigidezColumna:0.##} · {r.rigidezMuro:0.##} × Ig"));
            c.Add(KeyValue("G aplicada / ΣRz", $"{r.G_aplicada_kN:0} / {r.G_reaccion_kN:0} kN"));
            c.Add(KeyValue("Q aplicada / ΣRz", $"{r.Q_aplicada_kN:0} / {r.Q_reaccion_kN:0} kN"));
            c.Add(KeyValue("Corte basal EX · EY", $"{r.corteBasal_EX_kN:0} · {r.corteBasal_EY_kN:0} kN"));
            if (r.armadura != null && r.armadura.vigas > 0)
            {
                c.Add(KeyValue("Vigas DCR > 1", $"{r.armadura.vigas_DCR_mayor_1} de {r.armadura.vigas} (máx {r.armadura.DCR_max_viga:0.00} en {r.armadura.peorViga})"));
                c.Add(KeyValue("Columnas DCR > 1", $"{r.armadura.columnas_DCR_mayor_1} de {r.armadura.columnas} (máx {r.armadura.DCR_max_columna:0.00} en {r.armadura.peorColumna})"));
            }
            if (r.uMax != null)
                foreach (CaseMax u in r.uMax) c.Add(KeyValue("|u| máx " + u.caso, $"{u.u_mm:0.00} mm"));
        }

        if (Session.ScenarioLoaded)
        {
            c.Add(Title("ESCENARIO SIN GUARDAR"));
            c.Add(Text("Se está viendo el resultado del reanálisis. Guardarlo reemplaza el modelo vigente del proyecto " +
                       "(Assets/Resources/estructura_p1l4_unity.json, data/combinaciones.json y data/parametros_analisis.json).", "hint"));
            var keep = Row();
            keep.Add(Btn("Guardar como modelo vigente", () => { if (Session.SaveAsCurrent(viewer)) Rebuild(); }, "wide"));
            keep.Add(Btn("Descartar", () => Session.DiscardScenario(viewer), "wide"));
            c.Add(keep);
        }
    }

    private FloatField Factor(float value, System.Action<float> set)
    {
        var f = Input(new FloatField { value = value, formatString = "0.###" });
        f.AddToClassList("factor");
        f.style.width = 54; f.style.minWidth = 54; f.style.flexShrink = 0;
        f.RegisterCallback<AttachToPanelEvent>(_ =>
        {
            var input = f.Q(className: "unity-base-text-field__input");
            if (input != null) { input.style.width = 52; input.style.minWidth = 0; input.style.flexGrow = 1; }
        });
        f.RegisterValueChangedCallback(e => set(e.newValue));
        return f;
    }

    // ------------------------------------------------------------------
    // Propiedades del elemento seleccionado
    // ------------------------------------------------------------------
    private void BuildProps()
    {
        propsPanel = Panel("props");
        var head = new VisualElement();
        head.AddToClassList("props-head");
        propsTitle = Text("", "props-title");
        head.Add(propsTitle);
        head.Add(Btn("✕", () => picker?.ClearSelection(), "small"));
        propsPanel.Add(head);
        var scroll = new ScrollView(ScrollViewMode.Vertical);
        scroll.AddToClassList("props-scroll");
        propsBody = new VisualElement();
        propsBody.AddToClassList("props-body");
        scroll.Add(propsBody);
        propsPanel.Add(scroll);
        propsPanel.style.display = DisplayStyle.None;
        root.Add(propsPanel);
    }

    private void SyncProps()
    {
        string text = picker != null ? picker.InfoText : null;
        propsPanel.style.display = text == null ? DisplayStyle.None : DisplayStyle.Flex;
        propsPanel.style.width = UiTheme.InfoWidth;
        if (text == null || text == propsText) return;
        propsText = text;
        propsBody.Clear();

        VisualElement target = propsBody;
        foreach (string raw in text.Split('\n'))
        {
            string line = raw.Trim();
            if (line.Length == 0) continue;
            if (line.StartsWith("==="))
            {
                propsTitle.text = line.Trim('=', ' ');
                continue;
            }
            if (line.StartsWith("---") && line.EndsWith("---"))
            {
                string header = line.Trim('-', ' ');
                var fold = new Foldout { text = header.ToUpperInvariant(), value = !header.StartsWith("Trazabilidad") && !header.StartsWith("Ejes") };
                fold.AddToClassList("fold");
                propsBody.Add(fold);
                target = fold;
                continue;
            }
            target.Add(PropLine(line));
        }
    }

    /// "Clave: valor" o "Clave = valor" (una sola vez) como fila; si no, texto.
    private static VisualElement PropLine(string line)
    {
        int colon = line.IndexOf(':');
        int eq = line.IndexOf(" = ");
        bool oneColon = colon > 0 && colon < 30 && line.IndexOf(':', colon + 1) < 0 && !line.Contains("|");
        bool oneEq = eq > 0 && eq < 12 && line.IndexOf(" = ", eq + 3) < 0 && !line.Contains("|");
        if (oneColon) return KeyValue(line.Substring(0, colon).Trim(), line.Substring(colon + 1).Trim());
        if (oneEq) return KeyValue(line.Substring(0, eq).Trim(), line.Substring(eq + 3).Trim());
        return Text(line, "line");
    }

    // ------------------------------------------------------------------
    private void Update()
    {
        if (!Active) return;
        UpdateHostRect();
        if (Session.job.Running) Session.Poll(viewer);   // al terminar recarga el modelo (Rebuild)
        if (Time.unscaledTime < nextSync) return;
        nextSync = Time.unscaledTime + 0.2f;
        SyncAll();
    }

    private void SyncAll()
    {
        if (picker == null) picker = FindAnyObjectByType<ElementPicker>();
        diagrams = viewer.Diagrams;
        foreach (var s in syncers) s();
        SyncProps();
    }

    private void UpdateHostRect()
    {
        if (hosts.TryGetValue(ActiveTab, out VisualElement host) && host.panel != null)
        {
            Rect r = host.worldBound;   // unidades del panel = unidades GUI (ver Build)
            HostRect = new Rect(r.x, r.y + 4f, r.width, r.height);
        }
        else
        {
            HostRect = new Rect(-10000f, -10000f, 0f, 0f);   // paneles IMGUI fuera de pantalla
        }
    }

    /// true si la posicion (pixeles, origen abajo-izquierda) cae sobre la interfaz.
    public static bool IsPointerOverUI(Vector2 screenPos)
    {
        if (instance == null || instance.root?.panel == null) return false;
        IPanel panel = instance.root.panel;
        Vector2 p = RuntimePanelUtils.ScreenToPanel(panel, new Vector2(screenPos.x, Screen.height - screenPos.y));
        VisualElement picked = panel.Pick(p);
        return picked != null;
    }

    // ------------------------------------------------------------------
    // Fabricas de elementos
    // ------------------------------------------------------------------
    private static VisualElement Panel(string cls)
    {
        var v = new VisualElement();
        v.AddToClassList("panel");
        v.AddToClassList(cls);
        return v;
    }

    private static VisualElement Row()
    {
        var v = new VisualElement();
        v.AddToClassList("row");
        return v;
    }

    private static VisualElement Seg()
    {
        var v = new VisualElement();
        v.AddToClassList("seg");
        return v;
    }

    private static void FinishSeg(VisualElement seg)
    {
        if (seg.childCount == 0) return;
        seg[0].AddToClassList("seg-first");
        seg[seg.childCount - 1].AddToClassList("seg-last");
    }

    private static VisualElement Spacer()
    {
        var v = new VisualElement();
        v.AddToClassList("spacer");
        return v;
    }

    private static VisualElement Gap()
    {
        var v = new VisualElement();
        v.AddToClassList("seg-sep");
        return v;
    }

    private static Label Text(string text, params string[] classes)
    {
        var l = new Label(text);
        foreach (string c in classes) l.AddToClassList(c);
        return l;
    }

    private static Label Title(string text, bool first = false)
    {
        Label l = Text(text, "section-title");
        if (first) l.AddToClassList("first");
        return l;
    }

    private static Button Btn(string text, System.Action onClick, params string[] classes)
    {
        var b = new Button(onClick) { text = text };
        b.AddToClassList("btn");
        foreach (string c in classes) b.AddToClassList(c);
        return b;
    }

    private Toggle Check(string label, System.Func<bool> get, System.Action<bool> set)
    {
        var t = new Toggle(label) { value = get() };
        t.AddToClassList("chk");
        t.RegisterValueChangedCallback(e => set(e.newValue));
        syncers.Add(() => { if (t.value != get()) t.SetValueWithoutNotify(get()); });
        return t;
    }

    /// Texto visible en los campos de entrada (color, tamano y alto fijados en linea).
    private static T Input<T>(T field) where T : VisualElement
    {
        field.RegisterCallback<AttachToPanelEvent>(_ =>
        {
            var input = field.Q(className: "unity-base-text-field__input");
            if (input != null)
            {
                input.style.backgroundColor = new Color(0.055f, 0.082f, 0.137f);
                input.style.paddingLeft = 4; input.style.paddingRight = 4;
                input.style.paddingTop = 0; input.style.paddingBottom = 0;
                input.style.minHeight = 20;
            }
            var text = field.Q<TextElement>(className: "unity-text-element--inner-input-field-component");
            if (text != null)
            {
                text.style.color = new Color(0.9f, 0.93f, 0.97f);
                text.style.fontSize = 12;
                text.style.unityTextAlign = TextAnchor.MiddleLeft;
                text.style.flexGrow = 1;
            }
        });
        return field;
    }

    private static VisualElement KeyValue(string key, string value)
    {
        var row = new VisualElement();
        row.AddToClassList("kv");
        row.Add(Text(key, "k"));
        row.Add(Text(value, "v"));
        return row;
    }

    private static VisualElement Legend(Color color, string text)
    {
        var row = new VisualElement();
        row.AddToClassList("legend-row");
        var sw = new VisualElement();
        sw.AddToClassList("swatch");
        sw.style.backgroundColor = color;
        row.Add(sw);
        row.Add(Text(text, "legend-text"));
        return row;
    }
}
