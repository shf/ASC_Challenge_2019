import collections


class MeshImport():
    '''
    this class is for converting different mesh files to readable mesh file 
    in FEniCS. It also reads node sets from the mesh files.'''

    def __init__(self, FileAddress):
        self._FileAddress = FileAddress

    def UNVtoXMLConverter(self):
        UNVFile = open(self._FileAddress, "r").readlines()
        _flag = None
        _nodes = {}
        _connectivity = {}
        TriangleElement = False
        for line in UNVFile:
            temp = line.split()
            if "-1" in temp:
                _flag = None
            if _flag == "Nodes":
                if len(temp) == 4:
                    NodeID = temp[0]
                if len(temp) == 3:
                    _nodes[NodeID] = temp
            if _flag == "Elements":
                if len(temp) == 6:
                    if temp[5] == "3":
                        TriangleElement = True
                        CellID = temp[0]
                if len(temp) == 3 and TriangleElement:
                    _connectivity[CellID] = temp
                    TriangleElement = False
            if "2411" in line and len(temp) == 1:
                _flag = "Nodes"
            if "2412" in line and len(temp) == 1:
                _flag = "Elements"
        _SortedConnectivity = collections.OrderedDict(
            sorted(_connectivity.items()))
        self._connectivity = _SortedConnectivity
        self._Nodes=_nodes
        # writing xml file
        directory = self._FileAddress.split("/")
        directory.pop()
        directory.append("mesh.xml")
        XMLFile = open("/".join(directory), "w")
        XMLFile.write("<dolfin xmlns:dolfin=\"https://fenicsproject.org/\">\n")
        XMLFile.write("  <mesh celltype=\"triangle\" dim=\"3\">\n")
        XMLFile.write("    <vertices size=\"{}\">\n".format(len(_nodes)+1))
        for key, value in _nodes.items():
            XMLFile.write("      <vertex index=\"{}\" x=\"{}\" y=\"{}\" z=\"{}\"/>\n".format(
                key, value[0], value[1], value[2]))
        XMLFile.write("    </vertices>\n")
        XMLFile.write("    <cells size=\"{}\">\n".format(
            int(min(_SortedConnectivity.keys()))+len(_SortedConnectivity)))
        for key, value in _SortedConnectivity.items():
            XMLFile.write("      <triangle index=\"{}\" v0=\"{}\" v1=\"{}\" v2=\"{}\"/>\n".format(
                key, value[0], value[1], value[2]))
        XMLFile.write("    </cells>\n")
        XMLFile.write("  </mesh>\n")
        XMLFile.write("</dolfin>\n")
        XMLFile.close()
    
    def MeshData(self):
        return self._Nodes, self._connectivity


    def MeshGroups(self):
        UNVFile = open(self._FileAddress, "r").readlines()
        InGroup = False
        InSet = False
        _groups = collections.defaultdict(list)
        for line in UNVFile:
            temp = line.split()
            if "-1" in temp and len(temp) == 1:
                InGroup = False
            if InGroup == True:
                if InSet == True:
                    if len(temp) == 4:
                        _groups[SetName].append(temp[1])
                    elif len(temp) == 8:
                        _groups[SetName].append(temp[1])
                        _groups[SetName].append(temp[5])
                    else:
                        InSet = False
                if len(temp) <= 2:
                    SetName = '_'.join(temp)
                    InSet = True
            if "2467" in temp and len(temp) == 1:
                InGroup = True

        # Remove zero values
        for key, value in _groups.items():
            _groups[key] = list(filter(("0").__ne__, value))
        _Faces = {}
        if len(self._connectivity) > 1:
            for key, grp in _groups.items():
                n=1
                for value in self._connectivity.values():
                    isElem = all(elem in grp for elem in value)
                    if isElem == True:
                        n+=1
                        # 4 should be minimum elements with the given nodes
                        if n>=4:
                            _Faces[key] = grp
                            break
        for key in _Faces.keys():
            del _groups[key]
        for key, value in _Faces.items():
            _Faces[key]=list(map(int, value))
        for key, value in _groups.items():
            _groups[key]=list(map(int, value))
        return _groups, _Faces
