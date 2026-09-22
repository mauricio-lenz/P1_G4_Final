using UnityEngine;

public class ElementPicker : MonoBehaviour
{
    public Camera cam;
    public float maxDistance = 500f;
    public LayerMask selectableLayer = ~0;

    public ElementSelectable Selected { get; private set; }
    private Vector3 lastHitPoint;

    [Header("Info Panel")]
    public Vector2 panelOffset = new Vector2(24f, 18f);
    public Vector2 panelMinSize = new Vector2(380f, 0f);
    public float panelMaxWidthRatio = 0.42f;
    public int panelFontSize = 11;
    public float panelPaddingX = 18f;
    public float panelLineSpacing = 2f;
    public float panelSectionSpacing = 12f;

    private GUIStyle boxStyle;
    private GUIStyle labelStyle;
    private GUIStyle titleStyle;
    private GUIStyle headerStyle;
    private Vector2 scroll;

    void Awake()
    {
        if (cam == null)
        {
            cam = Camera.main;
        }
    }

    void Update()
    {
        if (cam == null)
        {
            cam = Camera.main;
            if (cam == null) return;
        }

        if (Input.GetMouseButtonDown(0))
        {
            Ray ray = cam.ScreenPointToRay(Input.mousePosition);
            if (Physics.Raycast(ray, out RaycastHit hit, maxDistance, selectableLayer))
            {
                var selectable = hit.collider.GetComponent<ElementSelectable>();
                if (selectable != null)
                {
                    Selected = selectable;
                    lastHitPoint = hit.point;
                    scroll = Vector2.zero;

                    if (selectedElement != null)
                    {
                        selectedElement.OnDeselected();
                    }
                    selectedElement = selectable;
                    selectable.OnSelected();

                    SetInfoSelection(null);

                    if (!string.IsNullOrEmpty(selectedElement.pmSectionId))
                    {
                        var pmPanel = FindObjectOfType<PMPanel>();
                        if (pmPanel != null)
                        {
                            pmPanel.ShowPMForElement(selectedElement);
                        }
                    }
                    return;
                }

                var info = hit.collider.GetComponent<InfoSelectable>();
                if (info != null)
                {
                    SetElementSelection(null);
                    selectedInfo = info;
                    scroll = Vector2.zero;
                    return;
                }
            }

            SetElementSelection(null);
            SetInfoSelection(null);
        }
    }

    private ElementSelectable selectedElement;
    private InfoSelectable selectedInfo;

    public void SelectElement(ElementSelectable sel, bool centerCamera)
    {
        if (sel == null)
        {
            SetElementSelection(null);
            return;
        }

        lastHitPoint = (sel.startPoint + sel.endPoint) * 0.5f;
        scroll = Vector2.zero;
        SetInfoSelection(null);
        SetElementSelection(sel);
        sel.OnSelected();

        var pmPanel = FindObjectOfType<PMPanel>();
        if (!string.IsNullOrEmpty(sel.pmSectionId))
        {
            if (pmPanel != null)
            {
                pmPanel.ShowPMForElement(sel);
            }
        }

        if (centerCamera && cam != null)
        {
            var orbit = cam.GetComponent<OrbitCamera>();
            if (orbit != null)
            {
                float length = Mathf.Max((sel.endPoint - sel.startPoint).magnitude, 8f);
                orbit.FocusOn(lastHitPoint, Mathf.Clamp(length * 4f, 18f, 90f));
            }
        }
    }

    private void SetElementSelection(ElementSelectable sel)
    {
        if (selectedElement != null)
        {
            selectedElement.OnDeselected();
        }
        selectedElement = sel;
        Selected = sel;

        if (sel == null)
        {
            var pmPanel = FindObjectOfType<PMPanel>();
            if (pmPanel != null)
            {
                pmPanel.Hide();
            }
        }
    }

    private void SetInfoSelection(InfoSelectable info)
    {
        selectedInfo = info;
        if (info != null)
        {
            scroll = Vector2.zero;
        }
    }

    void OnGUI()
    {
        if (Selected == null && selectedInfo == null) return;

        EnsureStyles();

        string info = Selected != null
            ? Selected.GetValuesAt(lastHitPoint)
            : $"==={selectedInfo.name}===\n{selectedInfo.GetInfo()}";
        float pmZone = Mathf.Min(440f, Screen.width * 0.42f) + 24f;
        float maxW = Screen.width - panelOffset.x * 2f - pmZone;
        float panelW = Mathf.Max(panelMinSize.x, Mathf.Min(Screen.width * 0.54f, maxW));
        float maxPanelH = Mathf.Max(280f, Screen.height - panelOffset.y * 2f - 82f);
        float panelH = Mathf.Min(Mathf.Max(480f, Screen.height * 0.86f), maxPanelH);

        float px = Screen.width - panelOffset.x - panelW;
        float py = Screen.height - panelOffset.y - panelH;

        GUI.Box(new Rect(px, py, panelW, panelH), GUIContent.none, boxStyle);

        float innerW = panelW - panelPaddingX * 2f;
        float contentH = CalculateContentHeight(info, innerW);
        if (contentH < panelH - 60f) contentH = panelH - 60f;

        var rect = new Rect(panelPaddingX, 0f, innerW, contentH);
        scroll = GUI.BeginScrollView(new Rect(px, py + 8f, panelW, panelH - 16f), scroll,
            new Rect(0f, 0f, panelW - 20f, contentH + 80f));

        int prevSize = labelStyle.fontSize;
        labelStyle.fontSize = panelFontSize;

        DrawLabel(info, rect, innerW, ref contentH);

        labelStyle.fontSize = prevSize;
        GUI.EndScrollView();
    }

    private void DrawLabel(string text, Rect area, float width, ref float yOffset)
    {
        string[] sections = text.Split('\n');
        float y = area.y;
        float lineH = panelFontSize + panelLineSpacing;

        foreach (string raw in sections)
        {
            string line = raw.TrimEnd('\r');
            bool isTitle = line.StartsWith("===");
            bool isHeader = line.StartsWith("---") && line.EndsWith("---");

            GUIStyle style = isTitle ? titleStyle : isHeader ? headerStyle : labelStyle;
            float styleLineH = isTitle || isHeader ? lineH + 2f : lineH;

            var content = new GUIContent(line);
            float h = style.CalcHeight(content, width);
            if (h < styleLineH) h = styleLineH;

            GUI.Label(new Rect(area.x, y, width, h), content, style);

            if (line == "" || line.Contains("---"))
            {
                y += h + panelSectionSpacing;
            }
            else
            {
                y += h + panelLineSpacing;
            }
        }

        yOffset = y - area.y;
    }

    private float CalculateContentHeight(string text, float width)
    {
        EnsureStyles();
        string[] sections = text.Split('\n');
        float y = 0f;
        float lineH = panelFontSize + panelLineSpacing;

        int prevLabelSize = labelStyle.fontSize;
        int prevTitleSize = titleStyle.fontSize;
        labelStyle.fontSize = panelFontSize;
        titleStyle.fontSize = panelFontSize + 2;
        headerStyle.fontSize = panelFontSize;

        foreach (string raw in sections)
        {
            string line = raw.TrimEnd('\r');
            bool isTitle = line.StartsWith("===");
            bool isHeader = line.StartsWith("---") && line.EndsWith("---");
            GUIStyle style = isTitle ? titleStyle : isHeader ? headerStyle : labelStyle;
            float styleLineH = isTitle || isHeader ? lineH + 2f : lineH;
            float h = style.CalcHeight(new GUIContent(line), width);
            if (h < styleLineH) h = styleLineH;
            y += h + ((line == "" || line.Contains("---")) ? panelSectionSpacing : panelLineSpacing);
        }

        labelStyle.fontSize = prevLabelSize;
        titleStyle.fontSize = prevTitleSize;
        headerStyle.fontSize = prevLabelSize;
        return y + 60f;
    }

    private void EnsureStyles()
    {
        if (boxStyle != null) return;

        boxStyle = new GUIStyle(GUI.skin.box);
        Texture2D bg = new Texture2D(1, 1);
        bg.SetPixel(0, 0, new Color(0.07f, 0.07f, 0.15f, 0.92f));
        bg.Apply();
        boxStyle.normal.background = bg;
        boxStyle.border = new RectOffset(2, 2, 2, 2);
        boxStyle.padding = new RectOffset(8, 8, 8, 8);

        labelStyle = new GUIStyle(GUI.skin.label);
        labelStyle.fontSize = panelFontSize;
        labelStyle.normal.textColor = Color.white;
        labelStyle.wordWrap = true;
        labelStyle.richText = false;
        labelStyle.alignment = TextAnchor.UpperLeft;
        labelStyle.padding = new RectOffset(0, 0, 0, 0);

        titleStyle = new GUIStyle(labelStyle);
        titleStyle.fontSize = panelFontSize + 2;
        titleStyle.fontStyle = FontStyle.Bold;
        titleStyle.normal.textColor = new Color(0.3f, 0.8f, 1f);

        headerStyle = new GUIStyle(labelStyle);
        headerStyle.fontStyle = FontStyle.Bold;
        headerStyle.normal.textColor = new Color(0.7f, 0.85f, 0.95f);
    }
}
