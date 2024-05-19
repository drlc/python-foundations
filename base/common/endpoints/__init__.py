import inspect


def get_all_by_class(module, class_name):
    endpoints = []

    for _, sub_module in inspect.getmembers(module):
        if inspect.ismodule(sub_module):
            members = dict(inspect.getmembers(sub_module))
            if class_name in members:
                endpoints.append(members[class_name]())

    return endpoints
