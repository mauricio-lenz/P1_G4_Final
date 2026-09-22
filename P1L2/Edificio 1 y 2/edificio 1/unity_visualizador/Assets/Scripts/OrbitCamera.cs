using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class OrbitCamera : MonoBehaviour
{
    public Transform target;
    public float distance = 10f;
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
            pivot.transform.position = new Vector3(3f, 1.6f, 2.5f);
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
#endif
        distance = Mathf.Clamp(distance - scroll * zoomSpeed, 5f, 120f);

        UpdatePosition();
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
}
