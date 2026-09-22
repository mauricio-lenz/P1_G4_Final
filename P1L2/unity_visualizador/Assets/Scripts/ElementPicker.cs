using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class ElementPicker : MonoBehaviour
{
    public Camera targetCamera;
    public string currentText = "Toca o haz click sobre una barra.";
    private Vector2 resultScroll;

    private void Awake()
    {
        if (targetCamera == null)
        {
            targetCamera = Camera.main;
        }
    }

    private void Update()
    {
#if ENABLE_INPUT_SYSTEM
        Mouse mouse = Mouse.current;
        if (mouse != null && mouse.leftButton.wasPressedThisFrame)
        {
            Pick(mouse.position.ReadValue());
        }

        Touchscreen touchscreen = Touchscreen.current;
        if (touchscreen != null && touchscreen.primaryTouch.press.wasPressedThisFrame)
        {
            Pick(touchscreen.primaryTouch.position.ReadValue());
        }
#else
        if (Input.GetMouseButtonDown(0))
        {
            Pick(Input.mousePosition);
        }

        if (Input.touchCount > 0 && Input.GetTouch(0).phase == TouchPhase.Began)
        {
            Pick(Input.GetTouch(0).position);
        }
#endif
    }

    private void Pick(Vector2 screenPosition)
    {
        Ray ray = targetCamera.ScreenPointToRay(screenPosition);

        RaycastHit[] hits = Physics.RaycastAll(ray, 200f);
        if (hits.Length == 0)
        {
            return;
        }

        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));

        foreach (RaycastHit hit in hits)
        {
            ElementSelectable selectable = hit.collider.GetComponent<ElementSelectable>();
            if (selectable == null)
            {
                continue;
            }

            currentText = selectable.GetValuesAt(hit.point);
            return;
        }

        foreach (RaycastHit hit in hits)
        {
            InfoSelectable info = hit.collider.GetComponent<InfoSelectable>();
            if (info == null)
            {
                continue;
            }

            currentText = info.GetInfo();
            return;
        }

        currentText = "Seleccionaste un objeto sin resultados.";
    }

    private void OnGUI()
    {
        float width = Mathf.Min(460f, Screen.width - 390f);
        if (width < 300f)
        {
            width = Screen.width - 40f;
        }

        float height = Mathf.Min(420f, Screen.height - 40f);
        float x = Mathf.Max(20f, Screen.width - width - 20f);
        Rect panelRect = new Rect(x, 20f, width, height);
        Rect scrollRect = new Rect(panelRect.x + 12f, panelRect.y + 32f, width - 24f, height - 44f);

        GUIStyle textStyle = new GUIStyle(GUI.skin.textArea)
        {
            wordWrap = true,
            alignment = TextAnchor.UpperLeft,
            padding = new RectOffset(10, 10, 10, 10)
        };

        float contentHeight = Mathf.Max(scrollRect.height - 20f, textStyle.CalcHeight(new GUIContent(currentText), scrollRect.width - 20f) + 20f);
        Rect viewRect = new Rect(0f, 0f, scrollRect.width - 20f, contentHeight);

        GUI.Box(panelRect, "Resultados seleccionados");
        resultScroll = GUI.BeginScrollView(scrollRect, resultScroll, viewRect);
        GUI.TextArea(viewRect, currentText, textStyle);
        GUI.EndScrollView();
    }
}
