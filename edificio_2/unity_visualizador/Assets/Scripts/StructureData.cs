using System;

[Serializable]
public class StructureData
{
    public string units;
    public NodeData[] nodes;
    public ElementData[] elements;
    public PointLoadData[] pointLoads;
    public SupportData[] supports;
    public RigidDiaphragmData[] rigidDiaphragms;
}

[Serializable]
public class RigidDiaphragmData
{
    public string id;
    public string level;
    public string type;
    public string load_profile;
    public float x1;
    public float x2;
    public float y1;
    public float y2;
    public float z;
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
    public string elementTag;
    public string sourceId;
    public string sectionId;
    public string materialId;
    public string type;
    public int nodeI;
    public int nodeJ;
    public float uniformLoad;
    public float tributaryArea;
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
}
