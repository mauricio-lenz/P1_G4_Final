using UnityEngine;

public class ElementSelectable : MonoBehaviour
{
    public ElementData data;
    public Vector3 startPoint;
    public Vector3 endPoint;
    public string customLabel;
    public bool isWall;
    public int wallId;
    public float wallThickness;
    public float wallLength;
    public string wallBottom;
    public string wallTop;
    public string wallSourceBuilding;
    public string wallSourceId;

    public string pmSectionId;
    public DemandRecord[] pmDemands;

    public SupportData nodeISupport;
    public SupportData nodeJSupport;
    public int nodeIId;
    public int nodeJId;

    private Color originalColor;
    private bool hasOriginalColor;

    public void OnSelected()
    {
        Renderer renderer = GetComponent<Renderer>();
        if (renderer != null && renderer.material != null)
        {
            if (!hasOriginalColor)
            {
                originalColor = renderer.material.color;
                hasOriginalColor = true;
            }
            renderer.material.color = Color.yellow;
        }
    }

    public void OnDeselected()
    {
        Renderer renderer = GetComponent<Renderer>();
        if (renderer != null && renderer.material != null && hasOriginalColor)
        {
            renderer.material.color = originalColor;
        }
    }

    public string GetValuesAt(Vector3 hitPoint)
    {
        if (isWall)
        {
            return GetWallValuesAt(hitPoint);
        }

        if (!string.IsNullOrEmpty(customLabel))
        {
            string customResult = customLabel;
            if (!string.IsNullOrEmpty(pmSectionId))
            {
                customResult += $"\nCurva P-M: {pmSectionId}";
            }
            DemandRecord demand = GetActiveWallDemand();
            if (demand != null)
            {
                customResult += $"\nDemanda {demand.combo}: P={demand.P_kN:0.##} kN | M={demand.M_kN_m:0.##} kN*m";
            }
            return customResult;
        }

        if (data == null)
        {
            return "Elemento sin datos.";
        }

        Vector3 axis = endPoint - startPoint;
        float t = axis.sqrMagnitude > 0.0001f
            ? Mathf.Clamp01(Vector3.Dot(hitPoint - startPoint, axis) / axis.sqrMagnitude)
            : 0.5f;
        float length = axis.magnitude;
        float localS = t * length;

        string tag = !string.IsNullOrEmpty(data.elementTag) ? data.elementTag : data.id.ToString();
        string secId = !string.IsNullOrEmpty(data.sectionId) ? data.sectionId : data.seccion;
        string building = !string.IsNullOrEmpty(data.sourceBuilding) ? data.sourceBuilding : "?";

        float n, vy, vz, my, mz, torsion;
        GetForces(t, length, out n, out vy, out vz, out my, out mz, out torsion);

        string result =
            $"=== Elemento {tag} ({data.type}) ===\n" +
            $"ID Unity: {gameObject.name}\n" +
            $"elementTag OpenSees: {tag}\n" +
            $"Nodo I: {data.nodeI}  Nodo J: {data.nodeJ}\n" +
            $"Piso: {data.piso ?? "-"}\n" +
            $"Edificio: {building}\n" +
            $"\n--- Seccion y Material ---\n" +
            $"Seccion: {secId} ({data.width_m:0.00} x {data.height_m:0.00} m)\n";

        var mat = UnityData.GetMaterial(secId);
        if (mat != null)
        {
            result += $"Material: {mat.materialName}\n" +
                      $"fc' = {mat.fc_MPa:0.0} MPa | fy = {mat.fy_MPa:0.0} MPa\n";
            if (mat.steelBars > 0)
            {
                result += $"Acero: {mat.steelBars} barras phi {mat.barDiameter_mm:0.0} mm\n" +
                          $"Ast = {mat.Ast_mm2:0.0} mm2 | rho = {mat.rho_percent:0.###}%\n";
            }
        }

        result += $"\n--- Restricciones ---\n";
        result += FormatSupport("Nodo I", nodeISupport);
        result += FormatSupport("Nodo J", nodeJSupport);

        result += $"\n--- Ejes Locales ---\n";
        Vector3 localX = axis.normalized;
        Vector3 localZ = Vector3.Cross(localX, Vector3.up).normalized;
        if (localZ.sqrMagnitude < 0.0001f)
        {
            localZ = Vector3.forward;
        }
        Vector3 localY = Vector3.Cross(localZ, localX).normalized;
        result += $"X' (axial): {localX.x:0.000}, {localX.z:0.000}, {localX.y:0.000} (global)\n" +
                  $"Y': {localY.x:0.000}, {localY.z:0.000}, {localY.y:0.000} (global)\n" +
                  $"Z': {localZ.x:0.000}, {localZ.z:0.000}, {localZ.y:0.000} (global)\n";

        result += $"\n--- Fuerzas en {t * 100f:0.0}% ({localS:0.00} m de {length:0.00} m) ---\n" +
                  $"N  = {n:0.###} kN\n" +
                  $"Vy = {vy:0.###} kN\n" +
                  $"Vz = {vz:0.###} kN\n" +
                  $"T  = {torsion:0.###} kN*m\n" +
                  $"My = {my:0.###} kN*m\n" +
                  $"Mz = {mz:0.###} kN*m\n";

        result += GetEndForcesText();

        if (data.type == "viga" && data.areaTributaria > 0f)
        {
            result += $"\n--- Cargas Tributarias ---\n" +
                      $"Area: {data.areaTributaria:0.###} m2\n" +
                      $"D: {data.deadLoad:0.###} kN | L: {data.liveLoad:0.###} kN\n" +
                      $"U=1.4D: {data.factoredLoad14D:0.###} kN\n" +
                      $"U=1.2D+1.6L: {data.factoredLoad12D16L:0.###} kN\n";
        }

        if (UnityData.ActiveCombo != null)
        {
            result += $"\n--- Demanda-capacidad ({UnityData.GetComboLabel(UnityData.ActiveCombo)}) ---\n";
            Vector2 pmDemand = !string.IsNullOrEmpty(pmSectionId)
                ? GetPMDemandForCase(UnityData.ActiveCombo)
                : new Vector2(-n, Mathf.Sqrt(my * my + mz * mz));
            float cRatio = GetCapacityRatio(pmDemand);
            result += $"P = {pmDemand.x:0.###} kN (compresion+)\n" +
                      $"M = {pmDemand.y:0.###} kN*m (resultante)\n" +
                      $"C = {cRatio:0.###} (M/Mcap)\n";

            if (!string.IsNullOrEmpty(pmSectionId))
            {
                result += $"Curva P-M: {pmSectionId}\n";
            }
        }

        if (!string.IsNullOrEmpty(pmSectionId))
        {
            result += GetComboBreakdownText();
        }

        result += $"\n--- Trazabilidad ---\n" +
                  $"OpenSees tag: {tag}\n" +
                  $"Unity obj: {gameObject.name}\n" +
                  "Resultado: " + UnityData.GetComboLabel(UnityData.ActiveCombo) + "\n" +
                  $"Seccion/Capacidad: {secId} -> {pmSectionId ?? "sin curva"}\n";

        return result;
    }

    private string GetEndForcesText()
    {
        if (data == null || string.IsNullOrEmpty(UnityData.ActiveCombo) || UnityData.ElementForcesByCombo == null)
        {
            return "";
        }
        float[] forces = UnityData.GetElementForces(UnityData.ActiveCombo, data.id);
        if (forces == null || forces.Length < 12)
        {
            return "  (sin registros de extremos para este elemento)\n";
        }
        string lbl = UnityData.GetComboLabel(UnityData.ActiveCombo);
        return $"\n--- Extremos ({lbl}) ---\n" +
               $"Nodo I ({data.nodeI}): N={forces[0]:0.###} Vy={forces[1]:0.###} Vz={forces[2]:0.###} T={forces[3]:0.###} My={forces[4]:0.###} Mz={forces[5]:0.###}\n" +
               $"Nodo J ({data.nodeJ}): N={forces[6]:0.###} Vy={forces[7]:0.###} Vz={forces[8]:0.###} T={forces[9]:0.###} My={forces[10]:0.###} Mz={forces[11]:0.###}\n";
    }

    private string GetComboBreakdownText()
    {
        if (data == null)
        {
            return "";
        }

        string combo = string.IsNullOrEmpty(UnityData.ActiveCombo) ? "C1" : UnityData.ActiveCombo;
        Vector2 g = GetPMDemandForCase("G");
        Vector2 q = GetPMDemandForCase("Q");
        Vector2 ex = GetPMDemandForCase("EX");
        Vector2 ey = GetPMDemandForCase("EY");
        Vector2 total = GetPMDemandForCase(combo);
        float cRatio = GetCapacityRatio(total);
        ComboInfo info = UnityData.GetComboInfo(combo);
        float fg = info != null ? info.G : 0f;
        float fq = info != null ? info.Q : 0f;
        float fex = info != null ? info.EX : 0f;
        float fey = info != null ? info.EY : 0f;

        return $"\n--- Valores P-M de {combo} ---\n" +
               $"Resultado: P={total.x:0.##} kN | M={total.y:0.##} kN*m | C={cRatio:0.###}\n" +
               $"G  x {fg:0.##}: P={g.x:0.##}, M={g.y:0.##}\n" +
               $"Q  x {fq:0.##}: P={q.x:0.##}, M={q.y:0.##}\n" +
               $"EX x {fex:0.##}: P={ex.x:0.##}, M={ex.y:0.##}\n" +
               $"EY x {fey:0.##}: P={ey.x:0.##}, M={ey.y:0.##}\n";
    }

    private float GetCapacityRatio(Vector2 demand)
    {
        if (string.IsNullOrEmpty(pmSectionId)) return 0f;
        PMCurveData curve = UnityData.GetPMCurve(pmSectionId);
        if (curve == null || curve.points == null || curve.points.Length < 2) return 0f;

        float p = demand.x;
        float mCap = 0f;
        for (int i = 0; i < curve.points.Length - 1; i++)
        {
            PMPoint a = curve.points[i];
            PMPoint b = curve.points[i + 1];
            float minP = Mathf.Min(a.P_kN, b.P_kN);
            float maxP = Mathf.Max(a.P_kN, b.P_kN);
            if (p < minP || p > maxP) continue;

            float t = Mathf.Abs(b.P_kN - a.P_kN) > 0.001f
                ? Mathf.InverseLerp(a.P_kN, b.P_kN, p)
                : 0f;
            mCap = Mathf.Lerp(a.M_kN_m, b.M_kN_m, t);
            break;
        }

        if (mCap <= 0.001f)
        {
            float best = float.MaxValue;
            foreach (PMPoint pt in curve.points)
            {
                float dist = Mathf.Abs(pt.P_kN - p);
                if (dist < best)
                {
                    best = dist;
                    mCap = pt.M_kN_m;
                }
            }
        }

        return mCap > 0.001f ? demand.y / mCap : 0f;
    }

    private Vector2 GetPMDemandForCase(string caseName)
    {
        if (data == null || string.IsNullOrEmpty(caseName))
        {
            return Vector2.zero;
        }
        float[] forces = UnityData.GetElementForces(caseName, data.id);
        if (forces == null || forces.Length < 6)
        {
            return Vector2.zero;
        }
        float pComp = -forces[0];
        float mTotal = Mathf.Sqrt(forces[4] * forces[4] + forces[5] * forces[5]);
        return new Vector2(pComp, mTotal);
    }

    private string GetWallValuesAt(Vector3 hitPoint)
    {
        Vector3 axis = endPoint - startPoint;
        Vector3 localX = axis.sqrMagnitude > 0.0001f ? axis.normalized : Vector3.right;
        Vector3 localY = Vector3.up;
        Vector3 localZ = Vector3.Cross(localX, localY).normalized;
        if (localZ.sqrMagnitude < 0.0001f)
        {
            localZ = Vector3.forward;
        }

        DemandRecord demand = GetActiveWallDemand();
        float n = demand != null ? demand.P_kN : 0f;
        float vy = 0f;
        float vz = demand != null ? demand.V_kN : 0f;
        float torsion = 0f;
        float my = demand != null ? demand.M_kN_m : 0f;
        float mz = 0f;

        string source = !string.IsNullOrEmpty(wallSourceBuilding) ? wallSourceBuilding : "?";
        string sourceId = !string.IsNullOrEmpty(wallSourceId) ? wallSourceId : wallId.ToString();
        string secId = !string.IsNullOrEmpty(pmSectionId) ? pmSectionId : "MURO_EQ";
        string result =
            $"=== Muro {wallId} ===\n" +
            $"ID Unity: {gameObject.name}\n" +
            $"ID origen: {sourceId}\n" +
            $"Nodo I: {nodeIId}  Nodo J: {nodeJId}\n" +
            $"Tramo: {wallBottom} -> {wallTop}\n" +
            $"Edificio: {source}\n" +
            $"\n--- Seccion y Material ---\n" +
            $"Seccion: {secId}\n" +
            $"Geometria: t={wallThickness:0.###} m | L={wallLength:0.###} m\n" +
            $"Material: H-30 / Acero A630-420 (muro equivalente)\n" +
            $"fc' = 30.0 MPa | fy = 420.0 MPa\n";

        PMCurveData curve = UnityData.GetPMCurve(pmSectionId);
        if (curve != null)
        {
            result += $"Acero ref.: {curve.steelBars} barras phi {curve.barDiameter_mm:0.0} mm\n" +
                      $"Ast = {curve.Ast_mm2:0.0} mm2 | rho = {curve.rho_percent:0.###}%\n";
        }

        result += $"\n--- Restricciones ---\n";
        result += FormatSupport("Nodo I", nodeISupport);
        result += FormatSupport("Nodo J", nodeJSupport);

        result += $"\n--- Ejes Locales ---\n" +
                  $"X' (largo/base): {localX.x:0.000}, {localX.z:0.000}, {localX.y:0.000} (global)\n" +
                  $"Y' (vertical): {localY.x:0.000}, {localY.z:0.000}, {localY.y:0.000} (global)\n" +
                  $"Z' (espesor): {localZ.x:0.000}, {localZ.z:0.000}, {localZ.y:0.000} (global)\n";

        string combo = string.IsNullOrEmpty(UnityData.ActiveCombo) ? "C1" : UnityData.ActiveCombo;
        result += $"\n--- Fuerzas (muro equivalente, combo {UnityData.GetComboLabel(combo)}) ---\n" +
                  $"N  = {n:0.###} kN (compresion+)\n" +
                  $"Vz = {vz:0.###} kN (corte en plano del muro)\n" +
                  $"My = {my:0.###} kN*m (momento en plano)\n" +
                  $"Vy = {vy:0.###} kN (fuera de plano, despreciable)\n" +
                  $"T  = {torsion:0.###} kN*m (despreciable)\n" +
                  $"Mz = {mz:0.###} kN*m (fuera de plano, despreciable)\n";

        if (!string.IsNullOrEmpty(pmSectionId))
        {
            result += $"\nCurva P-M: {pmSectionId}\n";
        }
        if (demand != null && !string.IsNullOrEmpty(demand.note))
        {
            result += $"Nota demanda: {demand.note}\n";
        }

        result += $"\n--- Trazabilidad ---\n" +
                  $"OpenSees/JSON origen: {sourceId}\n" +
                  $"Unity obj: {gameObject.name}\n" +
                  $"Resultado: {UnityData.GetComboLabel(combo)}\n" +
                  $"Seccion/Capacidad: {secId}\n";
        return result;
    }

    private void GetForces(float t, float length, out float n, out float vy, out float vz, out float my, out float mz, out float torsion)
    {
        n = 0f; vy = 0f; vz = 0f; my = 0f; mz = 0f; torsion = 0f;

        if (!string.IsNullOrEmpty(UnityData.ActiveCombo) && UnityData.ElementForcesByCombo != null)
        {
            var forces = UnityData.GetElementForces(UnityData.ActiveCombo, data.id);
            if (forces != null && forces.Length >= 12)
            {
                float nI = forces[0], nJ = forces[6];
                float vyI = forces[1], vyJ = forces[7];
                float vzI = forces[2], vzJ = forces[8];
                float tI = forces[3], tJ = forces[9];
                float myI = forces[4], myJ = forces[10];
                float mzI = forces[5], mzJ = forces[11];

                n = Mathf.Lerp(nI, nJ, t);
                vy = Mathf.Lerp(vyI, vyJ, t);
                vz = Mathf.Lerp(vzI, vzJ, t);
                torsion = Mathf.Lerp(tI, tJ, t);
                my = Mathf.Lerp(myI, myJ, t);
                mz = Mathf.Lerp(mzI, mzJ, t);

                if (data.type == "viga" && Mathf.Abs(data.uniformLoad) > 1e-9f)
                {
                    mz += Mathf.Abs(data.uniformLoad) * length * length * t * (1f - t) / 2f;
                }
                return;
            }
        }

        n = Mathf.Lerp(data.axialI, data.axialJ, t);
        vz = Mathf.Lerp(data.shearI, data.shearJ, t);
        my = Mathf.Lerp(data.momentI, data.momentJ, t);
        if (data.type == "viga" && Mathf.Abs(data.uniformLoad) > 1e-9f)
        {
            my += Mathf.Abs(data.uniformLoad) * length * length * t * (1f - t) / 2f;
        }
    }

    public Vector3 GetDemandPoint()
    {
        if (data == null)
        {
            DemandRecord wallDemand = GetActiveWallDemand();
            return wallDemand == null ? Vector3.zero : new Vector2(wallDemand.P_kN, wallDemand.M_kN_m);
        }

        if (data == null || string.IsNullOrEmpty(UnityData.ActiveCombo) || UnityData.ElementForcesByCombo == null)
        {
            return Vector3.zero;
        }

        float[] forces = UnityData.GetElementForces(UnityData.ActiveCombo, data.id);
        if (forces == null || forces.Length < 6)
        {
            return Vector3.zero;
        }

        float pComp = -forces[0];
        float mTotal = Mathf.Sqrt(forces[4] * forces[4] + forces[5] * forces[5]);
        return new Vector2(pComp, mTotal);
    }

    public DemandRecord GetActiveWallDemand()
    {
        if (pmDemands == null || pmDemands.Length == 0)
        {
            return null;
        }
        string active = string.IsNullOrEmpty(UnityData.ActiveCombo) ? pmDemands[0].combo : UnityData.ActiveCombo;
        foreach (DemandRecord demand in pmDemands)
        {
            if (demand != null && demand.combo == active)
            {
                return demand;
            }
        }
        return pmDemands[0];
    }

    public Vector2 GetActiveDemand()
    {
        if (isWall)
        {
            DemandRecord wallDemand = GetActiveWallDemand();
            return wallDemand == null ? Vector2.zero
                                      : new Vector2(wallDemand.P_kN, wallDemand.M_kN_m);
        }
        return GetPMDemandForCase(string.IsNullOrEmpty(UnityData.ActiveCombo) ? "C1" : UnityData.ActiveCombo);
    }

    public float GetActiveUtilization()
    {
        if (string.IsNullOrEmpty(pmSectionId))
        {
            return 0f;
        }
        return GetCapacityRatio(GetActiveDemand());
    }

    private string FormatSupport(string label, SupportData support)
    {
        if (support == null)
        {
            return $"{label}: sin apoyo registrado\n";
        }

        bool fixedAll = support.ux == 1 && support.uy == 1 && support.uz == 1;
        string type = !string.IsNullOrEmpty(support.type) ? support.type :
                      (fixedAll ? "Empotrado" : $"ux={support.ux} uy={support.uy} uz={support.uz}");
        return $"{label} (N{support.node}): {type}\n";
    }
}
