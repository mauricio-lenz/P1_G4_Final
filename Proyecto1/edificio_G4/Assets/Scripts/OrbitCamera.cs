using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class OrbitCamera : MonoBehaviour
{
    public Transform target;
    public float distance = 75f;
    public float xSpeed = 120f;
    public float ySpeed = 80f;
    public float zoomSpeed = 4f;
    public float panSpeed = 8f;

    private float x = 45f;
    private float y = 28f;

    private void Start()
    {
        if (target == null)
        {
            GameObject pivot = new GameObject("CameraPivot");
            pivot.transform.position = new Vector3(-0.7f, 5f, -4.5f);
            target = pivot.transform;
        }

        UpdatePosition();
    }

    private void LateUpdate()
    {
#if ENABLE_INPUT_SYSTEM
        Mouse mouse = Mouse.current;
        if (mouse != null && mouse.rightButton.isPressed)
        {
            Vector2 delta = mouse.delta.ReadValue();
            x += delta.x * xSpeed * Time.deltaTime;
            y -= delta.y * ySpeed * Time.deltaTime;
            y = Mathf.Clamp(y, -10f, 80f);
        }

        // Pan con el boton central (arrastrar para moverse lateralmente).
        if (mouse != null && mouse.middleButton.isPressed)
        {
            Vector2 delta = mouse.delta.ReadValue();
            Vector2 pan = -delta * panSpeed * Time.deltaTime;
            Pan(pan.x, pan.y);
        }

        // Pan con las flechas del teclado (moverse por los lados).
        Keyboard keyboard = Keyboard.current;
        if (keyboard != null)
        {
            float ax = 0f;
            float ay = 0f;
            if (keyboard.rightArrowKey.isPressed) ax += 1f;
            if (keyboard.leftArrowKey.isPressed) ax -= 1f;
            if (keyboard.upArrowKey.isPressed) ay += 1f;
            if (keyboard.downArrowKey.isPressed) ay -= 1f;
            if (ax != 0f || ay != 0f)
            {
                Pan(ax * panSpeed * Time.deltaTime, ay * panSpeed * Time.deltaTime);
            }
        }

        float scroll = mouse != null ? mouse.scroll.ReadValue().y / 120f : 0f;
        HandleTouch();   // toques del celular (API Input legacy, activa en modo "Both")
#else
        if (Input.GetMouseButton(1))
        {
            x += Input.GetAxis("Mouse X") * xSpeed * Time.deltaTime;
            y -= Input.GetAxis("Mouse Y") * ySpeed * Time.deltaTime;
            y = Mathf.Clamp(y, -10f, 80f);
        }

        if (Input.GetMouseButton(2))
        {
            Vector2 pan = -new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y"));
            Pan(pan.x * panSpeed, pan.y * panSpeed);
        }

        float ax = (Input.GetKey(KeyCode.RightArrow) ? 1f : 0f) - (Input.GetKey(KeyCode.LeftArrow) ? 1f : 0f);
        float ay = (Input.GetKey(KeyCode.UpArrow) ? 1f : 0f) - (Input.GetKey(KeyCode.DownArrow) ? 1f : 0f);
        if (ax != 0f || ay != 0f)
        {
            Pan(ax * panSpeed * Time.deltaTime, ay * panSpeed * Time.deltaTime);
        }

        float scroll = Input.GetAxis("Mouse ScrollWheel");
        HandleTouch();
#endif
        distance = Mathf.Clamp(distance - scroll * zoomSpeed, 5f, 120f);

        UpdatePosition();
    }

    // ------------------------------------------------------------------
    // Celular: 1 dedo = orbitar, 2 dedos = pellizco (zoom) + arrastre (paneo).
    // Los toques que empiezan sobre un panel no mueven la camara.
    // ------------------------------------------------------------------
    public float touchOrbitSpeed = 0.25f;   // grados por pixel
    public float touchPanSpeed = 0.0025f;   // fraccion de la distancia por pixel
    private bool touchOrbitActive;
    private bool twoFingerActive;

    private void HandleTouch()
    {
        if (Input.touchCount == 0)
        {
            touchOrbitActive = false;
            twoFingerActive = false;
            return;
        }

        var picker = FindAnyObjectByType<ElementPicker>();
        bool infoVisible = picker != null && picker.Selected != null;

        if (Input.touchCount == 1)
        {
            UnityEngine.Touch t = Input.GetTouch(0);
            if (t.phase == UnityEngine.TouchPhase.Began)
            {
                touchOrbitActive = !UiTheme.IsOverUI(t.position, infoVisible);
            }
            if (touchOrbitActive && !twoFingerActive && t.phase == UnityEngine.TouchPhase.Moved)
            {
                x += t.deltaPosition.x * touchOrbitSpeed;
                y = Mathf.Clamp(y - t.deltaPosition.y * touchOrbitSpeed, -10f, 80f);
            }
            if (t.phase == UnityEngine.TouchPhase.Ended || t.phase == UnityEngine.TouchPhase.Canceled)
            {
                twoFingerActive = false;
            }
            return;
        }

        UnityEngine.Touch a = Input.GetTouch(0);
        UnityEngine.Touch b = Input.GetTouch(1);
        if (b.phase == UnityEngine.TouchPhase.Began)
        {
            twoFingerActive = !UiTheme.IsOverUI((a.position + b.position) * 0.5f, infoVisible);
        }
        if (!twoFingerActive) return;
        touchOrbitActive = false;

        Vector2 prevA = a.position - a.deltaPosition;
        Vector2 prevB = b.position - b.deltaPosition;
        float prevDist = (prevA - prevB).magnitude;
        float dist = (a.position - b.position).magnitude;
        if (prevDist > 1f && dist > 1f)
        {
            distance = Mathf.Clamp(distance * prevDist / dist, 5f, 120f);
        }
        Vector2 move = (a.deltaPosition + b.deltaPosition) * 0.5f;
        Pan(-move.x * touchPanSpeed * distance, -move.y * touchPanSpeed * distance);
    }

    private void Pan(float screenX, float screenY)
    {
        Quaternion rotation = Quaternion.Euler(y, x, 0f);
        Vector3 right = rotation * Vector3.right;
        Vector3 up = rotation * Vector3.up;

        Vector3 offset = right * screenX + up * screenY;
        target.position += offset;
    }

    private void UpdatePosition()
    {
        Quaternion rotation = Quaternion.Euler(y, x, 0f);
        Vector3 offset = rotation * new Vector3(0f, 0f, -distance);
        transform.position = target.position + offset;
        transform.rotation = rotation;
    }

    public void FocusOn(Vector3 point, float newDistance = -1f)
    {
        if (target == null)
        {
            GameObject pivot = new GameObject("CameraPivot");
            target = pivot.transform;
        }
        target.position = point;
        if (newDistance > 0f)
        {
            distance = Mathf.Clamp(newDistance, 5f, 120f);
        }
        UpdatePosition();
    }

    public void SetPreset(string preset)
    {
        if (preset == "TOP") { x = 0f; y = 80f; }
        else if (preset == "FRONT") { x = 0f; y = 8f; }
        else if (preset == "RIGHT") { x = 90f; y = 8f; }
        else if (preset == "ISO") { x = 45f; y = 30f; }
        UpdatePosition();
    }
}
