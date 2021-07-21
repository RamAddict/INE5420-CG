import builtins
from os import path
from typing import Sequence, Tuple, Dict, Generator

from graphics import Drawable, Point, Line, Polygon, Wireframe, Color
from utilities import iter_no_str


class _ObjDescriptor:
    def __init__(
        self,
        name: str,
        kind: str = None,
        vertex_indexes: Sequence[int] = None,
        attributes: Dict[str, str] = None,
    ):
        self.kind = kind or None
        self.vertex_indexes = vertex_indexes or []
        self.attributes = attributes or {}
        self.attributes['name'] = name


class ObjFile:
    """Python 'File-like Object' interface for Wavefront's OBJ format."""

    def __init__(self, file, mode, **kwargs):
        self.file = file
        self.mode = mode
        if self.mode in ('r', 'r+'):  # eager parse XXX: we don't treat errors
            self._descriptors, self._vertices, self._globals = _parse_objs(file)
        else:  # lazy write
            assert self.mode in ('w', 'w+')
            self._descriptors = []
            self._vertices = [None]
            self._globals = kwargs

    def __iter__(self) -> Generator:
        for obj in self._descriptors:
            yield self._obj_to_drawable(obj)

    def _obj_to_drawable(self, obj: _ObjDescriptor) -> Tuple[Drawable, Dict]:
        drawable: Drawable = None
        if obj.kind == 'point':
            v = self._vertices[obj.vertex_indexes[0]]
            drawable = Point(*v)
        elif obj.kind == 'line':
            a = self._vertices[obj.vertex_indexes[0]]
            b = self._vertices[obj.vertex_indexes[1]]
            drawable = Line(Point(*a), Point(*b))
        elif obj.kind in ('wireframe', 'polygon'):
            points = [Point(*(self._vertices[v])) for v in obj.vertex_indexes]
            if obj.kind == 'polygon': drawable = Polygon(points)
            else: drawable = Wireframe(points)
        return drawable, obj.attributes

    def read(self) -> Sequence[Tuple[Drawable, Dict]]:
        assert self.mode in ('r', 'r+')
        return [obj for obj in self]

    def write(self, drawable: Drawable, name: str, **kwargs):
        assert self.mode in ('w', 'w+', 'r+')
        self._descriptors.append(self._drawable_to_obj(drawable, name, **kwargs))

    def _drawable_to_obj(self, drawable: Drawable, name: str, **kwargs) -> _ObjDescriptor:
        obj = _ObjDescriptor(name=name, attributes=kwargs)
        # make sure we register vertices before indexing them
        if isinstance(drawable, Point):
            obj.kind = 'point'
            self._vertices.append(Point(*drawable))
            obj.vertex_indexes = [len(self._vertices) - 1]
        elif isinstance(drawable, Line):
            obj.kind = 'line'
            a, b = drawable
            self._vertices += [Point(*a), Point(*b)]
            n = len(self._vertices) - 1
            obj.vertex_indexes = [n - 1, n]
        elif isinstance(drawable, Wireframe):
            obj.kind = 'polygon' if isinstance(drawable, Polygon) else 'wireframe'
            for p in drawable:
                self._vertices.append(Point(*p))
                obj.vertex_indexes.append(len(self._vertices) - 1)
        return obj

    def close(self):
        if self.mode in ('w', 'w+', 'r+') and len(self._descriptors) > 0:
            _dump_objs(self.file, self._descriptors, self._vertices, self._globals)
        return self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.mode in ('w', 'w+', 'r+') and len(self._descriptors) > 0:
            _dump_objs(self.file, self._descriptors, self._vertices, self._globals)
        return self.file.__exit__(exc_type, exc_value, traceback)

    @property
    def closed(self) -> bool:
        return self.file.closed


def open(path, mode: str = 'r', **kwargs):
    if mode.lower() not in ('r', 'r+' 'w', 'w+'):
        raise ValueError("File mode should be one of 'r', 'r+', 'w' or 'w+'")
    else:
        return ObjFile(builtins.open(path, mode), mode, **kwargs)


def _parse_objs(file) -> Tuple[Sequence[_ObjDescriptor], Sequence[Point], Dict]:
    descriptors = []
    vertices = [None]
    globals_ = {}

    materials: Dict[str, Color] = {}

    # if we never see an 'o', assume the entire file's an object
    current_obj = _ObjDescriptor(name=path.basename(file.name).split('.')[0])
    for line in file:
        # skip empty lines
        words = line.strip().split()
        if not words: continue

        head, *body = words
        if head == '#':
            continue
        elif head == 'mtllib':
            dirname = path.dirname(path.abspath(file.name))
            for libname in body:
                globals_['mtllib'] = list(body)
                libpath = dirname + '/' + libname
                with builtins.open(libpath, 'r') as lib:
                    mtl = None
                    for line in lib:
                        words = line.strip().split()
                        if not words or head == '#':
                            continue
                        elif words[0] == 'newmtl':
                            mtl = words[1]
                        elif words[0] == 'Kd':
                            assert mtl is not None
                            color = Color(*map(lambda x: int(float(x)*0xFF), words[1:]))
                            materials[mtl] = color
                            mtl = None
        elif head == 'v':
            x, y, *_ = body
            vertices.append(Point(float(x), float(y)))
        elif head == 'o':
            # before starting an object, we need to "finish" the current one
            if current_obj is not None and current_obj.kind is not None:
                descriptors.append(current_obj)
            # start a new object with partial information
            current_obj = _ObjDescriptor(name=body[0])
        elif head == 'usemtl':
            assert current_obj is not None
            mtl = body[0]
            current_obj.attributes['usemtl'] = mtl
            current_obj.attributes['color'] = materials[mtl]
        elif head == 'p':
            assert current_obj is not None
            current_obj.kind = 'point'
            current_obj.vertex_indexes.append(int(body[0]))
        elif head == 'l':
            assert current_obj is not None
            current_obj.kind = 'wireframe' if len(body) > 2 else 'line'
            for v in body:
                current_obj.vertex_indexes.append(int(v))
        elif head == 'f':
            assert current_obj is not None
            current_obj.kind = 'polygon'
            for v in body:
                current_obj.vertex_indexes.append(int(v))

    if current_obj is not None:  # also close obj on end on file
        descriptors.append(current_obj)

    return descriptors, vertices, globals_


def _dump_objs(file, descriptors: _ObjDescriptor, vertices: Sequence[Point], globals_: Dict):
    # emit vertices
    for vertex in vertices[1:]:
        x, y, *z = vertex
        z = z[0] if z else 1.0
        file.write(f"v {x} {y} {z} 1.0\n")

    # emit global configs
    for head in globals_.keys():
        file.write(head + " ")
        for body in iter_no_str(globals_[head]): file.write(body + " ")
        file.write("\n")

    # then, emit each individual object
    for obj in descriptors:
        file.write(f"o {obj.attributes['name']}\n")

        for key in obj.attributes.keys():
            if key in ('name', 'color'): continue
            file.write(key + " ")
            for val in iter_no_str(obj.attributes[key]): file.write(val + " ")
            file.write("\n")

        kind = obj.kind.lower()
        if kind == 'point':
            file.write(f"p {obj.vertex_indexes[0]}\n")
        elif kind == 'line':
            a, b = obj.vertex_indexes
            file.write(f"l {a} {b}\n")
        elif kind == 'wireframe':
            file.write(" ".join(["l"] + [str(v) for v in obj.vertex_indexes]))
            file.write("\n")
        elif kind == 'polygon':
            file.write(" ".join(["f"] + [str(v) for v in obj.vertex_indexes]))
            file.write("\n")
