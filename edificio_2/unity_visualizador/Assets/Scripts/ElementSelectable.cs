using UnityEngine;

public class ElementSelectable : MonoBehaviour
{
    public ElementData data;
    public Vector3 startPoint;
    public Vector3 endPoint;

    public string GetValuesAt(Vector3 hitPoint)
    {
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

        string elementTag = string.IsNullOrEmpty(data.elementTag) ? data.sourceId : data.elementTag;
        string tributaryText = $"\nelementTag: {elementTag}\nSeccion: {data.sectionId}\nMaterial: {data.materialId}";
        if (data.type == "viga")
        {
            float length = axis.magnitude;
            float maxMoment = Mathf.Abs(data.uniformLoad) * length * length / 8f;
            float maxShear = Mathf.Abs(data.uniformLoad) * length / 2f;
            tributaryText +=
                $"\nCarga aplicada qU: {data.uniformLoad:0.###} kN/m" +
                $"\nArea tributaria: {data.tributaryArea:0.###} m2" +
                $"\nD tributaria: {data.deadLoad:0.###} kN" +
                $"\nL tributaria: {data.liveLoad:0.###} kN" +
                $"\nU=1.4D: {data.factoredLoad14D:0.###} kN" +
                $"\nU=1.2D+1.6L: {data.factoredLoad12D16L:0.###} kN" +
                $"\nVmax aprox: {maxShear:0.###} kN" +
                $"\nMmax aprox: {maxMoment:0.###} kN*m";
        }
        else if (data.type == "columna")
        {
            tributaryText +=
                $"\nCarga axial gravitacional acumulada: {Mathf.Abs(data.axialI):0.###} kN" +
                $"\nCorte: {shear:0.###} kN" +
                $"\nMomento: {moment:0.###} kN*m" +
                $"\nNota: corte y momento requieren analisis lateral/marco completo.";
        }

        return $"Elemento {data.id} ({data.type})\n" +
               $"Posicion: {t * 100f:0}%\n" +
               $"Axial en punto N: {axial:0.###} kN\n" +
               $"Corte en punto Vz: {shear:0.###} kN\n" +
               $"Momento en punto My: {moment:0.###} kN*m" + tributaryText;
    }
}
