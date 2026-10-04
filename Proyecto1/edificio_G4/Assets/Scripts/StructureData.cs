using System;
using UnityEngine;

[Serializable]
public class StructureData
{
    public string units;
    public float q_G;
    public float Q_kN_m2;
    public float Q_cubierta_kN_m2;   // sobrecarga del nivel superior (cubierta)
    public float seismic_coefficient;
    public AnalysisSummary resumenAnalisis;
    public string p1l4_version;
    public NodeData[] nodes;
    public ElementData[] elements;
    public WallData[] walls;
    public SupportData[] supports;
    public DiaphragmData[] diaphragmList;
    public SlabData[] slabs;
    public TributaryFloorData[] tributaryList;
    public PointLoadData[] pointLoads;

    public P1L4Extras p1l4;
}

/// Resumen que agrega exportar_resultados_unity.py (equilibrio, corte basal, |u| max).
[Serializable]
public class AnalysisSummary
{
    public float q_G_kN_m2;
    public float Q_kN_m2;
    public float coeficienteSismico;
    public float G_aplicada_kN;
    public float G_reaccion_kN;
    public float Q_aplicada_kN;
    public float Q_reaccion_kN;
    public float corteBasal_EX_kN;
    public float corteBasal_EY_kN;
    public CaseMax[] uMax;
    public SectionChange[] secciones;
    public ArmaduraSummary armadura;
    public float rigidezViga = 1f, rigidezColumna = 1f, rigidezMuro = 1f;   // factores de inercia (1 = bruta)
    public SismoSummary sismo;
}

/// Sismo usado en el analisis: NCh433 estatico (C por edificio y direccion) o C fijo.
[Serializable]
public class SismoSummary
{
    public string metodo;          // "NCh433" o "fijo"
    public float C_fijo;
    public int zona;
    public string suelo;
    public float R, I, fraccionQ;
    public string hipotesis;
    public float C_equivalente_X, C_equivalente_Y;
    public SismoEdificio[] edificios;
}

[Serializable]
public class SismoEdificio
{
    public string edificio;
    public float P_kN, T_X_s, T_Y_s, C_X, C_Y, Q0_X_kN, Q0_Y_kN;
}

/// Armadura de vigas (inferior, superior, suple de apoyo, estribos) o columnas (barras, estribos).
[Serializable]
public class ArmaduraData
{
    public string inferior, superior, supleApoyo, estribosApoyo, estribosTramo;
    public string barras, estribos;
}

[Serializable]
public class CapacityCombo
{
    public string combo;
    public float Mu_pos, Mu_neg, Vu, DCR_flexion, DCR_corte;   // viga
    public float Pu, Mu, phiMn_at_Pu, phiVn, DCR_PM;            // columna
}

[Serializable]
public class CapacityData
{
    public ArmaduraData armadura;
    public float phiMn_pos_kN_m, phiMn_neg_kN_m, phiVn_apoyo_kN, phiVn_tramo_kN, As_inf_mm2, As_sup_apoyo_mm2;
    public float P0_kN, phiPmax_kN, Ast_mm2;
    public float DCR;
    public string comboGobernante;
    public CapacityCombo[] porCombo;

    public CapacityCombo ForCombo(string combo)
    {
        if (porCombo == null) return null;
        foreach (CapacityCombo c in porCombo) if (c.combo == combo) return c;
        return null;
    }
}

[Serializable]
public class ArmaduraSummary
{
    public int vigas, columnas, vigas_DCR_mayor_1, columnas_DCR_mayor_1;
    public float DCR_max_viga, DCR_max_columna;
    public string peorViga, peorColumna;
}

[Serializable]
public class CaseMax
{
    public string caso;
    public float u_mm;
}

[Serializable]
public class SectionChange
{
    public int id;
    public string tag;
    public string antes;
    public string despues;
}

[Serializable]
public class PointLoadData
{
    public int node;
    public float fx;
    public float fy;
    public float fz;
    public float mx;
    public float my;
    public float mz;
}

[Serializable]
public class DiaphragmData
{
    public string level;
    public float x;
    public float y;
    public float z;
    public int maestro;
    public int[] slaves;
}

[Serializable]
public class P1L4Extras
{
    public ComboInfo[] combinations;
    public DisplacementRecord[] displacements;
    public ElementForceRecord[] elementForces;
    public PMCurveData[] pmCurves;
    public SectionMaterialData[] sectionMaterials;
    public WallRegistryEntry[] wallRegistry;
    public MovingLoadData cargaMovil;
}

// Sidequest carga movil: casos unitarios precalculados (carga_movil.py)
[Serializable]
public class MovingLoadData
{
    public float P_default_kN;
    public MovingLoadPath[] paths;
    public string nota;
}

[Serializable]
public class MovingLoadPath
{
    public string id;
    public string nombre;
    public string edificio;
    public string nivel;
    public float z;
    public int[] nodeIds;      // nodos del edificio (orden de disp)
    public int[] elementIds;   // elementos del edificio (orden de forces)
    public MovingLoadPoint origen;
    public float[] dir;
    public float largo;
    public MovingLoadBeam[] beams;
    public MovingLoadUnitCase[] unitCases;
    public MovingLoadCheck[] validacion;
}

[Serializable]
public class MovingLoadPoint
{
    public float x;
    public float y;
}

[Serializable]
public class MovingLoadBeam
{
    public int element;
    public string tag;
    public int nodeA;
    public int nodeB;
    public float s0;
    public float s1;
}

[Serializable]
public class MovingLoadUnitCase
{
    public int node;
    public string tipo;   // "F" = Fz unitaria hacia abajo, "M" = momento unitario en torno a z x dir
    public float sumRz;
    public float[] disp;  // ux, uy, uz por nodo (orden nodeIds)
    public float[] forces; // 12 fuerzas por elemento (orden elementIds)
}

[Serializable]
public class MovingLoadCheck
{
    public float s;
    public float sumRz_comb_kN;
    public float sumRz_directo_kN;
    public float errDisp_m;
    public float errReac_kN;
}

[Serializable]
public class ComboInfo
{
    public string name;
    public string label;
    public float G;
    public float Q;
    public float EX;
    public float EY;
}

[Serializable]
public class DisplacementRecord
{
    public string combo;
    public int node;
    public float ux;
    public float uy;
    public float uz;
    public float rx;
    public float ry;
    public float rz;
}

[Serializable]
public class ElementForceRecord
{
    public string combo;
    public int id;
    public float[] f;
}

[Serializable]
public class PMCurveData
{
    public string sectionId;
    public string elementType;
    public float b_m;
    public float h_m;
    public float fc_MPa;
    public float fy_MPa;
    public int steelBars;
    public float barDiameter_mm;
    public float Ast_mm2;
    public float rho_percent;
    public float Po_kN;
    public string interpretation;
    public PMPoint[] points;
    public DemandRecord[] demands;
}

[Serializable]
public class DemandRecord
{
    public string combo;
    public float P_kN;
    public float M_kN_m;
    public float V_kN;
    public string note;
}

[Serializable]
public class SectionMaterialData
{
    public string sectionId;
    public string elementType;
    public string materialName;
    public float fc_MPa;
    public float fy_MPa;
    public float E_MPa;
    public float b_m;
    public float h_m;
    public int steelBars;
    public float barDiameter_mm;
    public float Ast_mm2;
    public float rho_percent;
    public string note;
}

[Serializable]
public class WallRegistryEntry
{
    public int index;
    public int nodeI;
    public int nodeJ;
    public float grosor;
    public float longitud;
    public string bottom;
    public string top;
    public string pmSectionId;
    public bool hasCurve;
    public DemandRecord[] demands;
}

[Serializable]
public class SupportData
{
    public int node;
    public string type;
    public int ux;
    public int uy;
    public int uz;
    public int rx;
    public int ry;
    public int rz;
}

[Serializable]
public class NodeData
{
    public int id;
    public float x;
    public float y;
    public float z;
}

[Serializable]
public class ElementData
{
    public int id;
    public string type;
    public int nodeI;
    public int nodeJ;
    public string seccion;
    public string sectionId;
    public string elementTag;
    public string sourceBuilding;
    public string sourceId;
    public float width_m;
    public float height_m;
    public float uniformLoad;
    public float deadLoad;
    public float liveLoad;
    public float factoredLoad14D;
    public float factoredLoad12D16L;
    public float axialI;
    public float axialJ;
    public float shearI;
    public float shearJ;
    public float momentI;
    public float momentJ;
    public string piso;
    public float areaTributaria;
    public float cargaTributaria;
    public float selfWeight_kN;   // peso propio (G), repartido en el elemento
    public CapacityData capacidad; // armadura y capacidad ACI 318 (capacidad_ha.py)
    public string pmCurveId;       // curva P-M de diseno de la columna (seccion + armadura)
}

[Serializable]
public class WallData
{
    public int id;
    public int nodeI;
    public int nodeJ;
    public string type;
    public float grosor;
    public float longitud;
    public string bottom;
    public string top;
    public string sourceBuilding;
    public string sourceId;
    public DemandRecord[] demands;
}

[Serializable]
public class SlabData
{
    public string id;
    public string nivel;
    public float x0;
    public float y0;
    public float x1;
    public float y1;
    public float z;
}

[Serializable]
public class TributaryFloorData
{
    public string piso;
    public float area_total;
    public float carga_total;
    public int vigas;
}

[Serializable]
public class PMPoint
{
    public string label;
    public float P_kN;
    public float M_kN_m;
    public float phi_1_m;
}

// Carga en elemento: 12 casos unitarios del elemento elegido (carga_elemento.py)
[Serializable]
public class ElementLoadCases
{
    public string error;
    public int element;
    public string tag;
    public string type;
    public string edificio;
    public int nodeI;
    public int nodeJ;
    public float length;
    public int[] nodeIds;
    public int[] elementIds;
    public ElementLoadUnitCase[] unitCases;
}

[Serializable]
public class ElementLoadUnitCase
{
    public int node;
    public int dof;        // 0..5 = Fx, Fy, Fz, Mx, My, Mz unitarios (ejes globales del modelo)
    public float[] sumR;   // suma de reacciones Rx, Ry, Rz
    public float[] disp;   // ux, uy, uz por nodo (orden nodeIds)
    public float[] forces; // 12 fuerzas por elemento (orden elementIds)
}

// Quitar elemento: resultados del reanalisis (quitar_elemento.py)
[Serializable]
public class ElementRemovalResult
{
    public string error;
    public RemovedElementInfo[] removed;
    public RemovalCaseState[] estado;
    public float G_aplicada_kN;
    public float G_reaccion_kN;
    public float carga_perdida_kN;
    public int[] nodos_sin_elementos;
    public DisplacementRecord[] displacements;
    public ElementForceRecord[] elementForces;
}

[Serializable]
public class RemovedElementInfo
{
    public int id;
    public string tag;
    public string type;
}

[Serializable]
public class RemovalCaseState
{
    public string combo;
    public bool ok;
    public float u_max_m;
}
