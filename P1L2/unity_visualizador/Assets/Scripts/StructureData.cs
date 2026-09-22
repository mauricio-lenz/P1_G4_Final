using System;

[Serializable]
public class StructureData
{
    public string units;
    public float q_G;
    public NodeData[] nodes;
    public ElementData[] elements;
    public WallData[] walls;
    public SupportData[] supports;
    public DiaphragmData[] diaphragmList;
    public SlabData[] slabs;
    public TributaryFloorData[] tributaryList;
    public PointLoadData[] pointLoads;
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
