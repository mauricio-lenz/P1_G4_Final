using System;
using UnityEngine;

[Serializable]
public class StructureData
{
    public string units;
    public float q_G;
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
