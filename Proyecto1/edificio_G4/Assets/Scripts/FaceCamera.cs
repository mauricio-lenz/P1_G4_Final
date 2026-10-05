using UnityEngine;

/// Mantiene una etiqueta (TextMesh) mirando a la camara activa.
public class FaceCamera : MonoBehaviour
{
    private void LateUpdate()
    {
        Camera cam = Camera.main;
        if (cam == null) return;
        transform.rotation = Quaternion.LookRotation(transform.position - cam.transform.position, cam.transform.up);
    }
}
