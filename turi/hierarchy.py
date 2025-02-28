import logging

logging.basicConfig()
log = logging.getLogger('Hierarchy')
log.setLevel(logging.DEBUG)


class HierarchyError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class NoConcreteDispatch(HierarchyError):
    def __init__(self, msg):
        self.msg = msg


# TODO: How to deal with external packages?
# cls.super_class
# KeyError: u'com.google.protobuf.GeneratedMessageV3'
class Hierarchy:
    """
        This class deals with classes hierachy to address dynamic invokes
    """

    def __init__(self, project):
        self.project = project
        self.interface_implementers = {}
        self.sub_interfaces = {}
        self.dir_sub_interfaces = {}
        self.sub_classes = {}
        self.dir_sub_classes = {}
        # init data
        self.init_hierarchy()

    def init_hierarchy(self):
        for class_name, cls in self.project.classes.items():
            # resolvingLevel?
            if 'INTERFACE' in cls.attrs:
                self.interface_implementers[cls] = []
                self.dir_sub_interfaces[cls] = []
            else:
                self.dir_sub_classes[cls] = []

        for class_name, cls in self.project.classes.items():
            if self.has_super_class(cls):
                if 'INTERFACE' in cls.attrs:
                    # TODO
                    # super_interfaces
                    pass

                else:
                    super_class = self.project.classes[cls.super_class]
                    self.dir_sub_classes[super_class].append(cls)

                    for i_name in cls.interfaces:
                        # get interface
                        if i_name not in self.project.classes:
                            continue
                        i = self.project.classes[i_name]
                        self.interface_implementers[i].append(cls)

        # fill direct implementers with subclasses
        for class_name, cls in self.project.classes.items():
            if 'INTERFACE' in cls.attrs:
                implementers = self.interface_implementers[cls]
                s = set()

                for c in implementers:
                    s |= set(self.get_sub_classes_including(c))

                self.interface_implementers[cls] = list(s)

    def has_super_class(self, cls):
        if cls.super_class:
            try:
                self.project.classes[cls.super_class]
                return True
            except KeyError:
                pass

        return False

    def is_subclass_including(self, cls_child, cls_parent):
        parent_classes = self.get_super_classes_including(cls_child)

        if cls_parent in parent_classes:
            return True

        # FIXME
        # for cls in parent_classes:
        #     if is_phatom(cls):
        #         return True

        return False

    def is_subclass(self, cls_child, cls_parent):
        parent_classes = self.get_super_classes(cls_child)

        if cls_parent in parent_classes:
            return True

        # FIXME
        # for cls in parent_classes:
        #     if is_phatom(cls):
        #         return True

        return False

    def is_visible_method(self, cls, method):
        method_cls = self.project.classes[method.class_name]

        if not self.is_visible_class(cls, method_cls):
            return False

        if 'PUBLIC' in method.attrs:
            return True

        if 'PRIVATE' in method.attrs:
            return cls == method_cls

        # package visibility
        # FIXME
        package_from = cls.name.split('.')[:-1]
        package_to = method_cls.name.split('.')[:-1]

        if 'PROTECTED' in method.attrs:
            is_sub = self.is_subclass_including(cls, method_cls)
            is_same_package = package_from == package_to
            return is_sub or is_same_package

        return package_from == package_to

    def is_visible_class(self, cls_from, cls_to):
        if 'PUBLIC' in cls_to.attrs:
            return True

        if 'PROTECTED' in cls_to.attrs or 'PRIVATE' in cls_to.attrs:
            return False

        # package visibility
        # FIXME
        package_from = cls_from.name.split('.')[:-1]
        package_to = cls_to.name.split('.')[:-1]
        return package_from == package_to

    def get_super_classes(self, cls):
        if 'INTERFACE' in cls.attrs:
            raise HierarchyError('This is an Interface')

        super_classes = []

        current = cls
        try:
            while True:
                current = self.project.classes[current.super_class]
                super_classes.append(current)

        except KeyError:
            return super_classes

    def get_super_classes_including(self, cls):
        super_classes = self.get_super_classes(cls)
        res = []

        res.append(cls)
        res.extend(super_classes)

        return res

    def get_implementers(self, interface):
        if 'INTERFACE' not in interface.attrs:
            raise HierarchyError('This is not an interface')

        res_set = set()

        for i in self.get_sub_interfaces_including(interface):
            res_set |= set(self.interface_implementers[i])

        return list(res_set)

    def get_sub_interfaces_including(self, interface):
        res = self.get_sub_interfaces(interface)
        res.append(interface)

        return res

    def get_sub_interfaces(self, interface):
        if 'INTERFACE' not in interface.attrs:
            raise HierarchyError('This is not an interface')

        if interface in self.sub_interfaces:
            return self.sub_interfaces[interface]

        # Otherwise
        res = []
        for i in self.dir_sub_interfaces[interface]:
            res.extend(self.get_sub_interfaces_including(i))

        self.sub_interfaces[interface] = res
        return res

    def get_sub_classes(self, cls):
        if 'INTERFACE' in cls.attrs:
            raise HierarchyError('This is an Interface. Class needed')

        if cls in self.sub_classes:
            return self.sub_classes[cls]

        res = []
        for c in self.dir_sub_classes[cls]:
            # resolving level > HIERACHY?
            res.extend(self.get_sub_classes_including(c))

        self.sub_classes[cls] = res
        return res

    def get_sub_classes_including(self, cls):
        if 'INTERFACE' in cls.attrs:
            raise HierarchyError('This is an Interface. Class needed')

        res = []
        res.extend(self.get_sub_classes(cls))
        res.append(cls)

        return res

    def resolve_abstract_dispatch(self, cls, method):
        if 'INTERFACE' in cls.attrs:
            classes_set = set()
            for i in self.get_implementers(cls):
                classes_set |= set(self.get_sub_classes_including(i))
            classes = list(classes_set)
        else:
            classes = self.get_sub_classes_including(cls)

        res_set = set()
        for c in classes:
            if 'ABSTRACT' not in c.attrs:
                res_set.add(self.resolve_concrete_dispatch(c, method))

        return list(res_set)

    def resolve_concrete_dispatch(self, cls, method):
        if 'INTERFACE' in cls.attrs:
            raise HierarchyError('class needed!')

        for c in self.get_super_classes_including(cls):
            for m in c.methods:
                if m.name == method.name and m.params == method.params:
                    if self.is_visible_method(c, method):
                        return m

        raise NoConcreteDispatch('1!!!!!!!Could not resolve concrete dispatch!')

    def resolve_special_dispatch(self, method, container):
        # container is the method that contains the invoke
        method_cls = self.project.classes[method.class_name]
        container_cls = self.project.classes[container.class_name]

        if method.name == '<init>' and ('java.lang.Runnable' in method_cls.interfaces or 'okhttp3.Callback' in method_cls.interfaces):
            # async framework
            for m in method_cls.methods:
                if m.name == "run":
                    method = self.project.methods[(m.class_name, m.name, m.params)]
                    return method

        if method.name == '<init>' and ('io.reactivex.SingleOnSubscribe' in method_cls.interfaces or 'io.reactivex.ObservableOnSubscribe' in method_cls.interfaces):
            # Rxjava
            for m in method_cls.methods:
                if m.name == "subscribe":
                    method = self.project.methods[(m.class_name, m.name, m.params)]
                    return method
        
        if method.name == '<init>' or 'PRIVATE' in method.attrs:
            return method

        elif self.is_subclass(method_cls, container_cls):
            return self.resolve_concrete_dispatch(container_cls, method)

        else:
            return method

    # Generic method to resolve invoke
    # Given an invoke expression it figures out which "technique" should apply
    def resolve_invoke(self, invoke_expr, method, container):
        invoke_type = str(type(invoke_expr))
        cls = self.project.classes[method.class_name]

        if 'VirtualInvokeExpr' in invoke_type:
            targets = self.resolve_abstract_dispatch(cls, method)

        elif 'DynamicInvokeExpr' in invoke_type:
            targets = self.resolve_abstract_dispatch(cls, method)

        elif 'InterfaceInvokeExpr' in invoke_type:
            targets = self.resolve_abstract_dispatch(cls, method)

        elif 'SpecialInvokeExpr' in invoke_type:
            t = self.resolve_special_dispatch(method, container)
            targets = [t]

        elif 'StaticInvokeExpr' in invoke_type:
            targets = [method]

        return targets
