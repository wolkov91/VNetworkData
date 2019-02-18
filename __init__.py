#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
from PyQt5.QtQml import qmlRegisterType, qmlRegisterUncreatableType

from .src.abstract_model import VAbstractNetworkDataModel
from .src.action import VAbstractAsynchronousAction, VAsynchronousAction, VNetworkAction, VNetworkModelAction
from .src.client import VAbstractNetworkClient
from .src.mixin import VAbstractNetworkDataModelMixin, VChildrenLoadingInfo, isAncestor, isDescendant
from .src.namespace import Vns
from .src.pagination import (VAbstractPagination, VAllTogetherPagination, VNothingPagination,
        VPagesAccumulationPagination, VPagesReplacementPagination)


author = 'Volkov Semyon'
"""Автор библиотеки."""


name = "VNetworkData"
"""Название библиотеки."""


# Семантическое версионирование:
# https://habr.com/company/Voximplant/blog/281593/
# https://semver.org/lang/ru/
# https://semver.org/lang/ru/spec/v2.0.0-rc.2.html


major = 0
"""Старший номер версии. 
Увеличивается, когда API меняется обратно несовместимым образом.
"""


minor = 8
"""Средний номер версии. 
Увеличивается, когда в API добавляется новая функциональность без нарушения обратной совместимости.
"""


patch = 0
"""Младший номер версии.
Увеличивается при исправлении багов, рефакторинге и прочих изменениях, которые не нарушают обратную совместимость, 
но и новую функциональность не добавляют.
"""


preRelease = "alpha"
"""Необязательный, разделенный точками список, отделенный от трех номеров версии знаком минус.
Используется вместо тегов, чтобы "помечать" определенные вехи в разработке. 
Обычно это "alpha", "beta", "release candidate" ("rc") и производные от них.
"""


meta = "data.time"
"""Необязательный, разделенный точками список, отделенный от предыдущей части версии знаком плюс.
По феншую сюда должен идти номер сборки.
"""


version = '{major}.{minor}'.format(major=major, minor=minor)
"""Версия в кратком формате ``major.minor``."""


release = '{major}.{minor}.{patch}-{preRelease}+{meta}'.format(
        major=major, minor=minor, patch=patch, preRelease=preRelease, meta=meta)
"""Полная версия в формате ``major.minor.patch-preRelease+meta``."""


def registerTypesForQml():
    """Регистрирует классы библиотеки VNetworkData в мета-объектной системе Qt для их использования в QML."""
    uri = name

    qmlRegisterUncreatableType(Vns, uri, major, minor, "Vns",
            "Vns is an enum container and can not be constructed.")

    # qmlRegisterUncreatableType(VAbstractNetworkClient, uri, major, minor, "VAbstractNetworkClient",
    #         "VAbstractNetworkClient is abstract and it can not be instantiated.")

    # qmlRegisterUncreatableType(VNetworkModelAction, uri, major, minor, "VNetworkModelAction",
    #         "VNetworkModelAction should not be instantiated in QML directly.")
    # qmlRegisterUncreatableType(VNetworkModelExpandedAction, uri, major, minor, "VNetworkModelExpandedAction",
    #         "VNetworkModelExpandedAction should not be instantiated in QML directly.")

    # qmlRegisterUncreatableType(VAbstractPagination, uri, major, minor, "VAbstractPagination",
    #         "VAbstractPagination is abstract and it can not be instantiated.")
    qmlRegisterType(VAllTogetherPagination, uri, major, minor, "VAllTogetherPagination")
    qmlRegisterType(VNothingPagination, uri, major, minor, "VNothingPagination")
    qmlRegisterType(VPagesAccumulationPagination, uri, major, minor, "VPagesAccumulationPagination")
    qmlRegisterType(VPagesReplacementPagination, uri, major, minor, "VPagesReplacementPagination")
