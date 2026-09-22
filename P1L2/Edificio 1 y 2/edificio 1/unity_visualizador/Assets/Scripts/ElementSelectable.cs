using UnityEngine;

public class ElementSelectable : MonoBehaviour
{
    public ElementData data;
    public Vector3 startPoint;
    public Vector3 endPoint;
    public string customLabel;

    public string GetValuesAt(Vector3 hitPoint)
    {
        if (!string.IsNullOrEmpty(customLabel))
        {
            return customLabel;
        }

        Vector3 axis = endPoint - startPoint;
        float t = Vector3.Dot(hitPoint - startPoint, axis) / axis.sqrMagnitude;
        t = Mathf.Clamp01(t);

        float axial = Mathf.Lerp(data.axialI, data.axialJ, t);
        float shear = Mathf.Lerp(data.shearI, data.shearJ, t);
        float moment = Mathf.Lerp(data.momentI, data.momentJ, t);
        if (data.type == "viga")
        {
            float length = axis.magnitude;
            moment += Mathf.Abs(data.uniformLoad) * length * length * t * (1f - t) / 2f;
        }

        string result = $"Elemento {data.id} ({data.type})\n" +
                       $"Posicion: {t * 100f:0}%\n" +
                       $"Axial N: {axial:0.###} kN\n" +
                       $"Corte Vz: {shear:0.###} kN\n" +
                       $"Momento My: {moment:0.###} kN*m";

        if (data.type == "viga" && data.areaTributaria > 0f)
        {
            result += $"\nArea tributaria: {data.areaTributaria:0.###} m2\n" +
                      $"Carga q_G: {data.cargaTributaria:0.##} kN";
        }

        return result;
    }
}
