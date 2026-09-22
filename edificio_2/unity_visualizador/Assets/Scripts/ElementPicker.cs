using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class ElementPicker : MonoBehaviour
{
    public Camera targetCamera;
    public string currentText = "Toca o haz click sobre una barra.";

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

        if (Physics.Raycast(ray, out RaycastHit hit, 200f))
        {
            ElementSelectable selectable = hit.collider.GetComponent<ElementSelectable>();
            if (selectable != null)
            {
                currentText = selectable.GetValuesAt(hit.point);
                return;
            }

            InfoSelectable info = hit.collider.GetComponent<InfoSelectable>();
            currentText = info != null ? info.GetInfo() : "Seleccionaste un objeto sin resultados.";
        }
    }

    private void OnGUI()
    {
        GUI.Box(new Rect(20, 20, 430, 210), currentText);
    }
}
