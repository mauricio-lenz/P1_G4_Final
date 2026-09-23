using UnityEngine;

public class ElementPicker : MonoBehaviour
{
    public Camera cam;
    public float maxDistance = 500f;
    public LayerMask selectableLayer = ~0;

    public ElementSelectable Selected { get; private set; }
    private Vector3 lastHitPoint;
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

        string info = Selected != null
            ? Selected.GetValuesAt(lastHitPoint)
            : $"==={selectedInfo.name}===\n{selectedInfo.GetInfo()}";

        Rect zone = UiTheme.InfoPanel();
        float panelW = zone.width;
        float panelH = zone.height - 8f;
        float px = zone.x;
        float py = zone.y + 4f;

        UiTheme.GUIBox(new Rect(px, py, panelW, panelH), "RESULTADOS DE ESFUERZOS");

        float innerW = panelW - UiTheme.SideM * 2f;
        float contentH = CalculateContentHeight(info, innerW);
        if (contentH < panelH - 40f) contentH = panelH - 40f;

        int prevSize = UiTheme.Label.fontSize;
        var rect = new Rect(px + UiTheme.SideM, 0f, innerW, contentH);
        scroll = GUI.BeginScrollView(new Rect(px, py + 28f, panelW, panelH - 34f), scroll,
            new Rect(0f, 0f, panelW - 14f, contentH + 80f));

        DrawLabel(info, rect, innerW, ref contentH);

        UiTheme.Label.fontSize = prevSize;
        GUI.EndScrollView();
    }

    private void DrawLabel(string text, Rect area, float width, ref float yOffset)
    {
        string[] sections = text.Split('\n');
        float y = area.y;
        float lineH = 14f;

        foreach (string raw in sections)
        {
            string line = raw.TrimEnd('\r');
            bool isTitle = line.StartsWith("===");
            bool isHeader = line.StartsWith("---") && line.EndsWith("---");

            GUIStyle style = isTitle ? UiTheme.TitleSm : isHeader ? UiTheme.Header : UiTheme.Label;
            float styleLineH = isTitle || isHeader ? lineH + 4f : lineH;

            var content = new GUIContent(line);
            float h = style.CalcHeight(content, width);
            if (h < styleLineH) h = styleLineH;

            GUI.Label(new Rect(area.x, y, width, h), content, style);

            if (line == "" || line.Contains("---"))
            {
                y += h + 10f;
            }
            else
            {
                y += h + 2f;
            }
        }

        yOffset = y - area.y;
    }

    private float CalculateContentHeight(string text, float width)
    {
        string[] sections = text.Split('\n');
        float y = 0f;
        float lineH = 14f;

        foreach (string raw in sections)
        {
            string line = raw.TrimEnd('\r');
            bool isTitle = line.StartsWith("===");
            bool isHeader = line.StartsWith("---") && line.EndsWith("---");
            GUIStyle style = isTitle ? UiTheme.TitleSm : isHeader ? UiTheme.Header : UiTheme.Label;
            float styleLineH = isTitle || isHeader ? lineH + 4f : lineH;
            float h = style.CalcHeight(new GUIContent(line), width);
            if (h < styleLineH) h = styleLineH;
            y += h + ((line == "" || line.Contains("---")) ? 10f : 2f);
        }

        return y + 40f;
    }
}
