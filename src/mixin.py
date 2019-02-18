#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
from typing import Callable

from PyQt5.QtCore import (QAbstractItemModel, QCoreApplication, QEventLoop, QModelIndex, QPersistentModelIndex,
                          QTimer, Qt, pyqtSignal, pyqtSlot)
from PyQt5.QtNetwork import QNetworkReply

from .action import VAbstractAsynchronousAction, VNetworkModelAction
from .namespace import Vns
from .pagination import VAbstractPagination


# TODO: Пока так помечаем то, что должно быть помечено через макрос Q_INVOKABLE.
vFromQmlInvokable = pyqtSlot


# TODO: Перенести в кокой-нибудь пакет с названием utils.py.
def _pathFromRoot(index: QModelIndex, showDisplayData: bool = True) -> str:
    """Возвращает путь от корня до элемента с модельным индексом `index`."""
    if index.isValid():
        # TODO: Надо избавиться от рекурсии - надо переписать с помощью цикла while!
        if showDisplayData:
            return "{parent} -> ({row},{column})'{name}'".format(
                    parent=_pathFromRoot(index.parent()), row=index.row(), column=index.column(),
                    name=index.data(Qt.DisplayRole))
        else:
            return "{parent} -> ({row},{column})".format(
                    parent=_pathFromRoot(index.parent()), row=index.row(), column=index.column())
    return "(-1,-1)'InvalidIndex'"


# TODO: Перенести в кокой-нибудь пакет с названием utils.py.
def isAncestor(ancestor: QModelIndex, descendant: QModelIndex) -> bool:
    """Возвращает True - если элемент с индексом `ancestor` является предком для элемента с индексом `descendant`,
    иначе - возвращает False."""
    if not descendant.isValid():
        return False
    if not ancestor.isValid():
        return True
    if ancestor.model() is not descendant.model():
        return False

    parent = descendant.parent()
    while parent.isValid():
        if parent == ancestor:
            return True
        parent = parent.parent()
    return False


# TODO: Перенести в кокой-нибудь пакет с названием utils.py.
# TODO: Неудачное название метода и его описание в доке?!
def isDescendant(descendant: QModelIndex, parent: QModelIndex, top: int, bottom: int, left: int, right: int,
        inclusive: bool = True) -> bool:
    """Возвращает True - если элемент с индексом `descendant` является потомком одного из элементов,
    находящихся в элементе с индексом `parent` между строками `top` и `bottom` включительно и
    между столбцами `left` и `right` включительно, иначе - возвращает False.

    Если `inclusive` является True (по умолчанию), то также вернет True, если элемент с индексом `descendant` является
    одним из самих элементов, находящихся в элементе с индексом `parent` между строками `top` и `bottom` включительно и
    между столбцами `left` и `right` включительно.
    """
    if not descendant.isValid():
        return False
    if parent.isValid() and parent.model() is not descendant.model():
        return False

    ancestor = descendant
    if not inclusive:
        ancestor = descendant.parent()
    while ancestor.isValid():
        if ancestor.parent() == parent and top <= ancestor.row() <= bottom and left <= ancestor.column() <= right:
            return True
        ancestor = ancestor.parent()
    return False


class VChildrenLoadingInfo:
    """Контейнер со вспомогательной (служебной) информацией о загрузке подэлементов."""

    def __init__(self, policy: Vns.LoadingPolicy, pagination: VAbstractPagination):
        """
        :param policy: Политика загрузки подэлементов.
        :param pagination: Пагинация подэлементов - хранит мета-информацию о загруженных данных.
        """
        super().__init__()

        self.inReloading = False  # Позволяет отличить перезагрузку подэлементов от прочих видов загрузок подэлементов.
        self.state = Vns.LoadingState.Idle
        self.policy = policy
        self.pagination = pagination


class VDetailsLoadingInfo:
    """Контейнер со вспомогательной (служебной) информацией о загрузке подробных данных об элементе."""

    def __init__(self):
        super().__init__()

        self.loaded = False  # Загружены ли подробные данные об элементе.
        self.state = Vns.LoadingState.Idle


class VAbstractNetworkDataModelMixin:
    """Абстрактная примесь к модели, определяющая интерфейс загрузки данных для модели из сети.

    Использует :class:`QNetworkReply`.

    Поддерживает древовидные модели.

    Поддерживает возможность настройки каждого элемента в модели по-отдельности.

    Загрузка подэлементов.
    ~~~~~~~~~~~~~~~~~~~~~~

    Чтобы позволить загружать подэлементы элементов, наследники класса должны переопределить абстрактные методы
    :func:`_getChildrenLoadingInfo()`, :func:`_requestToLoadingChildren()`, :func:`_appendChildren()` и
    :func:`_removeChildren()`.

    С помощью метода :func:`childrenAreLoadedSeparately()` можно определить, поддерживается ли загрузка подэлементов
    из конкретных элементов.

    Определить, есть ли уже загруженные подэлементы в элементах, можно с помощью метода :func:`hasLoadedChildren()`.

    Возможна автоматическая, ручная или смешанная загрузка подэлементов в элементах.
    Также можно запретить/приостановить дальнейшую (еще не запущенную) загрузку подэлементов.

    Автоматической загрузкой подэлементов управляют представления :class:`PyQt5.QtCore.QAbstractItemView` через
    методы модели :func:`hasChildren()`, :func:`canFetchMore()` и :func:`fetchMore()`.
    Пользователю эти методы модели также доступны.

    Для ручной загрузки подэлементов используются методы:
    # :func:`childrenAreLoadedSeparately()`, :func:`hasLoadedChildren()`,
    :func:`canReloadChildren()` и :func:`reloadChildren()`,
    :func:`canLoadNextChildren()` и :func:`loadNextChildren()`,
    :func:`canLoadPreviousChildren()` и :func:`loadPreviousChildren()`.

    .. note::
        Если проводить аналогии, то в контексте загрузки подэлементов методам
        :func:`hasChildren()`, :func:`canFetchMore()` и :func:`fetchMore()` соответствуют методы
        :func:`childrenAreLoadedSeparately()`, :func:`canLoadNextChildren()` и :func:`loadNextChildren()`.

    Ограничения и свободы действий загрузки подэлементов:
        - Из одного элемента одновременно может происходить только одно действие загрузки подэлементов.
        - Действие загрузки подэлементов из одного элемента независимо от действий загрузки подэлементов из любых других
          элементов, даже вложенных, то есть даже если они являются подэлементами элемента или его подэлементов и т.д.
        - Действие загрузки подэлементов независимо от любых других типов сетевых действий модели.

    Действие загрузки подэлементов, совершаемое из элемента, становится недействительным при удалении элемента.
    То есть при удалении элемента, если в нем совершается действие загрузки подэлементов, для этого действия испукается
    сигнал `VAbstractAsynchronousAction.invalidated`, затем прерывается его сетевой запрос, и действие удаляется
    без испускания сигнала `VAbstractAsynchronousAction.finished`.

    .. warning::
        Чтобы другие действия становились недействительными при удалении элемента, к которому они привязаны,
        их необходимо регистрировать в модели на время их выполнения с помощью метода :func:`_registerAction()`,
        и затем, после их завершения или инвалидации, отменять регистрацию с помощью метода :func:`_unregisterAction()`.

    Поддерживает различные типы пагинации при загрузке подэлементов.

    .. warning::
        Пагинация подэлементов должна быть установлена до первой загрузки подэлементов!

    Загрузка подробных данных об элементах.
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Чтобы позволить загружать подробные данные об элементах, наследники класса должны переопределить методы
    :func:`_getDetailsLoadingInfo()`, :func:`_requestToLoadingDetails()` и :func:`_updateDetails()`.
    Если модель не должна поддерживать загрузку подробных данных об элементах, то для этих методов будет достаточно
    базовой реализации, и переопределять их нет необходимости.

    С помощью метода :func:`detailsAreLoadedSeparately()` можно определить, поддерживается ли загрузка
    подробных данных для конкретных элементов.

    Определить, загружены ли подробные данные об элементах, можно с помощью метода :func:`hasLoadedDetails()`.

    Для загрузки подробных данных используются методы :func:`canReloadDetails()` и :func:`reloadDetails()`.

    Ограничения и свободы действий загрузки подробных данных:
        - Для одного элемента одновременно может происходить только одно действие загрузки подробных данных.
        - Действие загрузки подробных данных одного элемента независимо от действий загрузки подробных данных любых
          других элементов.
        - Действие загрузки подробных данных независимо от любых других типов сетевых действий модели.
          TODO: На данный момент при модификации элемента его модифицируемые данные не должны пересекаться с его подробными данными!
    """

    def __init__(self, *args, **kwargs):
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        super().__init__(*args, **kwargs)

        # Параметры последней произошедшей ошибки (храним данные только одной самой последней ошибки на всю модель):
        self.__errorType = Vns.ErrorType.NoError
        self.__errorInformativeText = ""
        self.__errorDetailedText = ""
        self.__errorPersistentModelIndex = QPersistentModelIndex()

        self.__actions = set()  # Множество зарегистрированных действий.

        self.modelAboutToBeReset.connect(self._invalidateAllActions)
        self.columnsAboutToBeRemoved.connect(self._invalidateActionsForColumns)
        self.rowsAboutToBeRemoved.connect(self._invalidateActionsForRows)

    # ===============
    # ==== error ====
    # ===============

    errorOccurred = pyqtSignal()
    """Сигнал о возникновении ошибки."""

    @vFromQmlInvokable(result=int)
    def errorType(self) -> int:
        """Возвращает тип последней ошибки."""
        return self.__errorType

    @vFromQmlInvokable(result=str)
    def errorInformativeText(self) -> str:
        """Возвращает общеописательный текст последней ошибки."""
        return self.__errorInformativeText

    @vFromQmlInvokable(result=str)
    def errorDetailedText(self) -> str:
        """Возвращает подробный текст последней ошибки."""
        return self.__errorDetailedText

    @vFromQmlInvokable(result=QModelIndex)
    def errorIndex(self) -> QModelIndex:
        """Возвращает модельный индекс элемента, в котором произошла последняя ошибка."""
        return QModelIndex(self.__errorPersistentModelIndex)

    def _setError(self, errorType: int, informativeText: str, detailedText: str = "",
            index: QModelIndex = QModelIndex()):
        """Устанавливает данные о последней ошибке и испускает сигнал `errorOccurred`.

        :param errorType: Тип ошибки.
        :param informativeText: Общеописательный текст ошибки.
        :param detailedText: Подробный текст ошибки.
        :param index: Модельный индекс элемента, в котором произошла ошибка.
        """
        self.__errorType = errorType
        self.__errorInformativeText = informativeText
        self.__errorDetailedText = detailedText
        self.__errorPersistentModelIndex = QPersistentModelIndex(index)
        self.errorOccurred.emit()

    def _resetError(self):
        """Сбрасывает данные о последней ошибке на значения по-умолчанию."""
        # self._setError(Vns.ErrorType.NoError, "", "", QModelIndex())
        self.__errorType = Vns.ErrorType.NoError
        self.__errorInformativeText = ""
        self.__errorDetailedText = ""
        self.__errorPersistentModelIndex = QPersistentModelIndex()

    # =================
    # ==== actions ====
    # =================

    def _actions(self) -> set:
        """Возвращает множество зарегистрированных действий."""
        return self.__actions

    # ==== registration of actions ====

    def _registerAction(self, action: VNetworkModelAction):
        """Регистрирует действие `action`."""
        assert action.getModel() is self
        assert action not in self.__actions
        self.__actions.add(action)
        # TODO: Мы не можем убрать из списка внезапно удаленные действия.
        # В С++ мы могли бы использовать какой-нибудь QPointer для отслеживания преждевременного удаления действия,
        # ну а в python-е как это отследить, если плюсовый объект и питоновский объект-обертка удаляются в разное время?
        # Сигнал destroyed тоже ничем не помогает, потому что содержит аргумент типа QObject на уровне С++,
        # и привести аргумент к нужному нам типу невозможно!
        # action.destroyed[QObject].connect(self._unregisterAction)
        # Не работает и такой способ: action.destroyed[VNetworkModelAction].connect(self._unregisterAction)

    def _unregisterAction(self, action: VNetworkModelAction):
        """Отменяет регистрацию действия `action`."""
        assert action.getModel() is self
        assert action in self.__actions
        self.__actions.remove(action)
        # TODO: Смотри описание проблемы в методе _registerAction()...
        # action.destroyed[QObject].disconnect(self._unregisterAction)

    # ==== invalidation of actions ====

    def _invalidateAllActions(self):
        """Помечает недействительными все незавершенные действия в модели."""
        for action in self.__actions:
            assert isinstance(action, VNetworkModelAction)
            if action.isValid() and action.isRunning():
                action.setInvalidated()

    def _invalidateActionsForItems(self, parent: QModelIndex, top: int, bottom: int, left: int, right: int):
        """Помечает недействительными все незавершенные действия, совершаемые над элементами, которые находятся
        в элементе с индексом `parent` между строками `top` и `bottom` включительно и между столбцами `left` и `right`
        включительно, а также все действия, совершаемые над всеми потомками этих элементов.
        """
        assert top <= bottom
        assert left <= right
        assert parent.model() is self if parent.isValid() else True
        for action in self.__actions:
            assert isinstance(action, VNetworkModelAction)
            if action.isValid() and action.isRunning():
                index = action.getIndex()
                if isDescendant(index, parent, top, bottom, left, right, inclusive=True):
                    action.setInvalidated()

    def _invalidateActionsForColumns(self, parent: QModelIndex, first: int, last: int) -> None:
        """Помечает недействительными все незавершенные действия, совершаемые над элементами, которые находятся
        в элементе с индексом `parent` в столбцах с `first` по `last` включительно, а также все действия,
        совершаемые над всеми потомками этих элементов.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        self._invalidateActionsForItems(parent, 0, self.rowCount(parent) - 1, first, last)

    def _invalidateActionsForRows(self, parent: QModelIndex, first: int, last: int) -> None:
        """Помечает недействительными все незавершенные действия, совершаемые над элементами, которые находятся
        в элементе с индексом `parent` в строках с `first` по `last` включительно, а также все действия,
        совершаемые над всеми потомками этих элементов.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        self._invalidateActionsForItems(parent, first, last, 0, self.columnCount(parent) - 1)

    # ==== deleting of actions ====

    def deleteActionLater(self, action: VAbstractAsynchronousAction):
        """Вызывает отложенное удаление действия `action` только в том случае, если данная модель является родителем
        этого действия.
        """
        if action.parent() is self:
            action.deleteLater()

    # ==== custom actions handling ====

    def _handleNotAccessibleNetwork(self, action: VNetworkModelAction) -> bool:
        """Если сеть недоступна, то обновляет данные об ошибке в действии `action`, прерывает сетевой запрос действия,
        завершает действие, обновляет данные об ошибке в модели и возвращает True, иначе - возвращает False.

        Это костыль для обхода багов в Qt:
            Если сеть недоступна или отключена, то сигнал `QNetworkReply.finished` почему-то испускается только
            из ОДНОГО ответа на сетевой запрос - самого первого завершенного по таймеру с момента отключения сети,
            из ВСЕХ ОСТАЛЬНЫХ ответов на сетевые запросы сигнал НЕ ИСПУСКАЕТСЯ.
            Поэтому действие сразу завершаем с ошибкой.

        .. warning::
            Данный метод должен вызываться непосредственно сразу после создания сетевого действия `action` и передачи
            в него ответа на его сетевой запрос.

        Пример:

        .. sourcecode::

            def removeItem(self, index: QModelIndex) -> VAbstractAsynchronousAction:
                assert index.isValid()
                reply = self.requestRemoving(index)
                assert isinstance(reply, QNetworkReply)
                action = VNetworkModelAction(model=self, index=QModelIndex(), reply=reply,
                                             type=Vns.ActionType.Custom, parent=self)
                if self._handleNotAccessibleNetwork(action):
                    return action
                # action.invalidated.connect(action.replyAbort)  # Как поведет себя сервер, если прервать запрос?
                action.replyFinished.connect(lambda: self._finishRemovingItem(action))
                self._registerAction(action)
                return action
        """
        assert action.getModel() is self if action.getModel() else True
        assert action.getIndex() is not None
        assert action.getIndex().model() is self if action.getIndex().isValid() else True
        reply = action._reply()
        assert reply and reply.isRunning()
        manager = reply.manager()
        if manager.networkAccessible() != manager.Accessible:
            reply.abort()
            errorType = Vns.ErrorType.NetworkError
            informativeText = QCoreApplication.translate("VAbstractNetworkDataModelMixin", "Доступ в сеть отключён.")
            detailedText = ""
            action.setError(errorType, informativeText, detailedText)
            self._setError(errorType, informativeText, detailedText, action.getIndex())
            action.finished.connect(lambda: self.deleteActionLater(action))
            QTimer.singleShot(0, action.setFinished)
            return True
        return False

    def _handleNetworkReplyError(self, action: VNetworkModelAction) -> bool:
        """В случае ошибки в сетевом ответе (т.е. в :class:`QNetworkReply`) при действии `action` - обновляет данные
        об ошибке в действии `action`, обновляет данные об ошибке в модели и возвращает True, иначе - возвращает False.

        .. warning::
            Данный метод должен вызываться после завершения сетевого ответа, принадлежащего действию `action`.

        Пример:

        .. sourcecode::

            def _finishRemovingItem(self, action: VNetworkModelAction):
                # action = self.sender()
                assert isinstance(action, VNetworkModelAction)
                if not action.isValid():
                    self._unregisterAction(action)
                    self.deleteActionLater(action)
                    return

                if not self._handleNetworkReplyError(action):
                    index = action.getIndex()
                    assert index.isValid()
                    self.removeLocalRow(index.row(), index.parent())
                self._unregisterAction(action)
                action.setFinished()
                self.deleteActionLater(action)
        """
        assert action.getModel() is self if action.getModel() else True
        assert action.getIndex() is not None
        assert action.getIndex().model() is self if action.getIndex().isValid() else True
        assert action._reply().isFinished() \
            if action._reply() and action._reply().manager().networkAccessible() == action._reply().manager().Accessible \
            else True  # Такое мудреное утверждение из-за багов в Qt при отключенной сети!
        if action.replyErrorType() != QNetworkReply.NoError:
            errorType = Vns.ErrorType.NetworkError
            informativeText = action.replyErrorString()
            detailedText = action.replyBodyStringData()
            action.setError(errorType, informativeText, detailedText)
            self._setError(errorType, informativeText, detailedText, action.getIndex())
            return True
        return False

    # =============================
    # ==== loading of children ====
    # =============================

    def _getChildrenLoadingInfo(self, index: QModelIndex = QModelIndex()) -> VChildrenLoadingInfo or None:
        """Возвращает контейнер со вспомогательной (служебной) информацией о загрузке подэлементов элемента
        с модельным индексом `index`.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `index`, возвращает None.

        Именно этот метод определяет, поддерживается ли загрузка подэлементов из конкретного элемента.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def childrenAreLoadedSeparately(self, parent: QModelIndex = QModelIndex()) -> bool:
        # TODO: Переименовать на childrenCanLoadedSeparately?
        """Возвращает True - если поддерживается загрузка подэлементов из элемента с модельным индексом `parent`,
        иначе - возвращает False.

        (Возвращает True - если подэлементы элемента с индексом `parent` загружаются отдельно, False - иначе.)

        .. note::
            Базовая реализация вызывает метод :func:`_getChildrenLoadingInfo()`.
            Вы можете переопределить это для ускорения работы данного метода.
        """
        return self._getChildrenLoadingInfo(parent) is not None

    # ==== childrenLoadingPolicy ====

    childrenLoadingPolicyChanged = pyqtSignal(QModelIndex, arguments=['parent'])
    """Сигнал об изменении политики загрузки подэлементов элемента.

    :param QModelIndex parent: Модельный индекс элемента.
    """

    @vFromQmlInvokable(result=int)
    @vFromQmlInvokable(QModelIndex, result=int)
    def childrenLoadingPolicy(self, parent: QModelIndex = QModelIndex()) -> Vns.LoadingPolicy:
        """Возвращает политику загрузки подэлементов из элемента с модельным индексом `parent`.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `parent`,
            возвращает `Vns.LoadingPolicy.DoNotLoad`.
        """
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        # if info is None:
        #     return Vns.LoadingPolicy.DoNotLoad
        # return info.policy
        return info.policy if info else Vns.LoadingPolicy.DoNotLoad

    @pyqtSlot(int, result=bool)
    @pyqtSlot(int, QModelIndex, result=bool)
    def setChildrenLoadingPolicy(self, policy: Vns.LoadingPolicy, parent: QModelIndex = QModelIndex()) -> bool:
        """Устанавливает политику `policy` загрузки подэлементов из элемента с модельным индексом `parent`.

        Возвращает True - если политика загрузки была установлена успешно, False - иначе.
        """
        return self._setChildrenLoadingPolicy(policy, parent)

    # rootChildrenLoadingPolicy = pyqtProperty(type=int, fget=getChildrenLoadingPolicy,
    #         fset=setChildrenLoadingPolicy, notify=childrenLoadingPolicyChanged,
    #         doc="Политика загрузки элементов модели (подэлементов корневого элемента модели).")

    def _setChildrenLoadingPolicy(self, policy: Vns.LoadingPolicy, parent: QModelIndex = QModelIndex(),
            info: VChildrenLoadingInfo = None) -> bool:
        """Устанавливает политику `policy` загрузки подэлементов из элемента с модельным индексом `parent`
        и информацией о загрузке подэлементов `info`.
        Если информация не указана, то она будет получена из элемента с индексом `parent`.

        Возвращает True - если политика загрузки была установлена успешно, False - иначе.
        """
        assert parent.model() is self if parent.isValid() else True
        if info is None:
            info = self._getChildrenLoadingInfo(parent)
            if info is None:
                return False
        assert info is self._getChildrenLoadingInfo(parent)
        if policy != info.policy:
            info.policy = policy
            self.childrenLoadingPolicyChanged.emit(parent)
        return True

    # def _resetChildrenLoadingPolicy(self, parent: QModelIndex = QModelIndex(), info: VChildrenLoadingInfo = None) -> bool:
    #     """Сбрасывает политику загрузки подэлементов из элемента с модельным индексом `parent`
    #     и информацией о загрузке подэлементов `info` на значение по-умолчанию.
    #     Если информация не указана, то она будет получена из элемента с индексом `parent`.
    #
    #     Возвращает True - если политика загрузки была сброшена успешно, False - иначе.
    #     """
    #     assert parent.model() is self if parent.isValid() else True
    #     if info is None:
    #         info = self._getChildrenLoadingInfo(parent)
    #         if info is None:
    #             return False
    #     assert info is self._getChildrenLoadingInfo(parent)
    #     if info.policy != info.DEFAULT_POLICY:
    #         info.policy = info.DEFAULT_POLICY
    #         self.childrenLoadingPolicyChanged.emit(parent)
    #     return True

    # ==== childrenLoadingState ====

    childrenLoadingStateChanged = pyqtSignal(QModelIndex, arguments=['parent'])
    """Сигнал об изменении состояния загрузки подэлементов элемента.

    :param QModelIndex parent: Модельный индекс элемента.
    """

    @vFromQmlInvokable(result=int)
    @vFromQmlInvokable(QModelIndex, result=int)
    def childrenLoadingState(self, parent: QModelIndex = QModelIndex()) -> Vns.LoadingState:
        """Возвращает состояние загрузки подэлементов из элемента с модельным индексом `parent`.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `parent`,
            возвращает `Vns.LoadingState.Unknown`.
        """
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        # if info is None:
        #     return Vns.LoadingState.Unknown
        # return info.state
        return info.state if info else Vns.LoadingState.Unknown

    # rootChildrenLoadingState = pyqtProperty(type=int, fget=getChildrenLoadingState,
    #         notify=childrenLoadingStateChanged,
    #         doc="Состояние загрузки модели (подэлементов корневого элемента модели). [Reed only]")

    def _setChildrenLoadingState(self, state: Vns.LoadingState, parent: QModelIndex = QModelIndex(),
            info: VChildrenLoadingInfo = None) -> bool:
        """Устанавливает состояние `state` загрузки подэлементов из элемента с модельным индексом `parent`
        и информацией о загрузке подэлементов `info`.
        Если информация не указана, то она будет получена из элемента с индексом `parent`.

        Возвращает True - если состояние загрузки было установлено успешно, False - иначе.
        """
        assert parent.model() is self if parent.isValid() else True
        if info is None:
            info = self._getChildrenLoadingInfo(parent)
            if info is None:
                return False
        assert info is self._getChildrenLoadingInfo(parent)
        if state != info.state:
            info.state = state
            self.childrenLoadingStateChanged.emit(parent)
        return True

    # def _resetChildrenLoadingState(self, parent: QModelIndex = QModelIndex(), info: VChildrenLoadingInfo = None) -> bool:
    #     """Сбрасывает состояние загрузки подэлементов из элемента с модельным индексом `parent`
    #     и информацией о загрузке подэлементов `info` на значение по-умолчанию.
    #     Если информация не указана, то она будет получена из элемента с индексом `parent`.
    #
    #     Возвращает True - если состояние загрузки было сброшено успешно, False - иначе.
    #     """
    #     assert parent.model() is self if parent.isValid() else True
    #     if info is None:
    #         info = self._getChildrenLoadingInfo(parent)
    #         if info is None:
    #             return False
    #     assert info is self._getChildrenLoadingInfo(parent)
    #     if info.resetState():
    #         self.childrenLoadingStateChanged.emit(parent)
    #     return True

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def childrenLoadingIsInIdleState(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если загрузка подэлементов элемента с индексом `parent` находится в состоянии покоя,
        иначе - возвращает False."""
        return self.childrenLoadingState(parent) == Vns.LoadingState.Idle

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def childrenLoadingIsInLoadingState(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если подэлементы элемента с индексом `parent` находятся в состоянии загрузки,
        иначе - возвращает False."""
        return self.childrenLoadingState(parent) == Vns.LoadingState.Loading

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def childrenLoadingIsInErrorState(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если загрузка подэлементов элемента с индексом `parent` находится в состоянии ошибки,
        иначе - возвращает False."""
        return self.childrenLoadingState(parent) == Vns.LoadingState.Error

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def childrenLoadingIsInUnknownState(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если загрузка подэлементов элемента с индексом `parent` находится в неизвестном состоянии,
        иначе - возвращает False."""
        return self.childrenLoadingState(parent) == Vns.LoadingState.Unknown

    # ==== childrenPagination ====

    # TODO: Нужен ли вообще этот сигнал?
    _childrenPaginationChanged = pyqtSignal(QModelIndex, arguments=['parent'])
    """Сигнал об изменении пагинации подэлементов элемента.

    :param QModelIndex parent: Модельный индекс элемента.
    """

    def childrenPagination(self, parent: QModelIndex = QModelIndex()) -> VAbstractPagination or None:
        """Возвращает пагинацию подэлементов элемента с модельным индексом `parent`.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `parent`, возвращает None.
        """
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        # if info is None:
        #     return None
        # return info.pagination
        return info.pagination if info else None

    # rootChildrenPagination = pyqtProperty(type=VAbstractPagination, fget=getChildrenPagination,
    #         # fset=_setChildrenPagination, notify=_childrenPaginationChanged,
    #         doc="Пагинация модели (подэлементов корневого элемента модели) - "
    #             "хранит мета-информацию о загруженных данных. [Reed only]")

    def _setChildrenPagination(self, pagination: VAbstractPagination, parent: QModelIndex = QModelIndex(),
            info: VChildrenLoadingInfo = None) -> bool:
        """Устанавливает пагинацию `pagination` подэлементов из элемента с модельным индексом `parent`
        и информацией о загрузке подэлементов `info`.
        Если информация не указана, то она будет получена из элемента с индексом `parent`.

        Возвращает True - если пагинация была установлена успешно, False - иначе.
        """
        assert parent.model() is self if parent.isValid() else True
        if info is None:
            info = self._getChildrenLoadingInfo(parent)
            if info is None:
                return False
        assert info is self._getChildrenLoadingInfo(parent)
        assert not pagination.hasLoadedData()  # Необходимо было вызвать pagination._resetAll() или создать новую пагинацию!
        assert not info.pagination.hasLoadedData()  # Необходимо было вызвать self._resetChildren(parent)!
        if pagination != info.pagination:
            info.pagination = pagination
            self._childrenPaginationChanged.emit(parent)
        return True

    # ==== loading of children methods ====

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def hasLoadedChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если в элементе с модельным индексом `parent` имеются уже загруженные подэлементы,
        иначе - возвращает False.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `parent`, возвращает False.
        """
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        if info is None:
            return False
        return info.pagination.hasLoadedData()

    childrenLoadingStarted = pyqtSignal(QModelIndex, arguments=['parent'])
    """Сигнал о начале загрузки подэлементов элемента.

    :param QModelIndex parent: Модельный индекс элемента.
    """

    childrenLoadingFinished = pyqtSignal(QModelIndex, arguments=['parent'])
    """Сигнал о завершении загрузки подэлементов элемента.

    :param QModelIndex parent: Модельный индекс элемента.
    """

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def canReloadChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если используется политика "ручной" загрузки подэлементов и если
        в данный момент можно перезагрузить подэлементы элемента с модельным индексом `parent`
        (перезагрузить, если подэлементы уже загружены, или загрузить, если они еще не загружены),
        иначе - возвращает False.
        """
        return self._canReloadChildren(parent, Vns.LoadingPolicy.Manually)

    def _canReloadChildren(self, parent: QModelIndex, policy: Vns.LoadingPolicy) -> bool:
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        if info is None:
            return False
        if policy not in info.policy:
            return False
        if info.state not in (Vns.LoadingState.Error, Vns.LoadingState.Idle):
            return False
        return info.pagination.canReloadData()

    @vFromQmlInvokable(result=VAbstractAsynchronousAction)
    @vFromQmlInvokable(QModelIndex, result=VAbstractAsynchronousAction)
    def reloadChildren(self, parent: QModelIndex = QModelIndex()) -> VAbstractAsynchronousAction:
        """Запускает асинхронную перезагрузку подэлементов из элемента с модельным индексом `parent`.
        (Перезагрузку, если подэлементы уже загружены, или загрузку, если они еще не загружены.)

        Загружаются ли все подэлементы или только их часть - зависит от пагинации.

        Если пагинация поддерживает много частей подэлементов и уже было загружено несколько из них,
        то все они будут удалены и только одна из них загружена снова.

        Возвращает экземпляр действия :class:`VAbstractAsynchronousAction`.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что его вызов разрешен.

            Это можно сделать, например, с помощью метода :func:`canReloadChildren()` с соответствующим аргументом,
            если используется политика "ручной" загрузки подэлементов  (т.е. `Vns.LoadingPolicy.Manually`).

        ..warning::
            Если родителем действия будет являться данная модель, то действие будет удалено сразу после завершения,
            иначе ответственность по его удалению будет лежать на Вас.
        """
        assert self._canReloadChildren(parent, Vns.LoadingPolicy.Automatically) \
               or self._canReloadChildren(parent, Vns.LoadingPolicy.Manually)
        info = self._getChildrenLoadingInfo(parent)
        assert info
        assert not info.inReloading
        info.inReloading = True
        info.pagination._requestToReloadingData()
        return self._loadChildren(parent)

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def canLoadNextChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если используется политика "ручной" загрузки подэлементов и если
        в данный момент можно загрузить следующую порцию подэлементов элемента с модельным индексом `parent`,
        иначе - возвращает False.
        """
        return self._canLoadNextChildren(parent, Vns.LoadingPolicy.Manually)

    def _canLoadNextChildren(self, parent: QModelIndex, policy: Vns.LoadingPolicy) -> bool:
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        if info is None:
            return False
        if policy not in info.policy:
            return False
        if info.state not in (Vns.LoadingState.Error, Vns.LoadingState.Idle):
            return False
        return info.pagination.canLoadNextData()

    @vFromQmlInvokable(result=VAbstractAsynchronousAction)
    @vFromQmlInvokable(QModelIndex, result=VAbstractAsynchronousAction)
    def loadNextChildren(self, parent: QModelIndex = QModelIndex()) -> VAbstractAsynchronousAction:
        """Запускает асинхронную загрузку следующей порции подэлементов из элемента с модельным индексом `parent`.

        Если до этого не было загружено ни одной из частей подэлементов, загружает первую из них.
        Если при этом пагинация поддерживает только загрузку всего и сразу, значит, будут загружены все подэлементы.

        Возвращает экземпляр действия :class:`VAbstractAsynchronousAction`.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что его вызов разрешен.

            Это можно сделать, например, с помощью метода :func:`canLoadNextChildren()` с соответствующим аргументом,
            если используется политика "ручной" загрузки подэлементов  (т.е. `Vns.LoadingPolicy.Manually`).

        ..warning::
            Если родителем действия будет являться данная модель, то действие будет удалено сразу после завершения,
            иначе ответственность по его удалению будет лежать на Вас.
        """
        assert self._canLoadNextChildren(parent, Vns.LoadingPolicy.Automatically) \
               or self._canLoadNextChildren(parent, Vns.LoadingPolicy.Manually)
        info = self._getChildrenLoadingInfo(parent)
        assert info
        info.pagination._requestToLoadingNextDataPart()
        return self._loadChildren(parent)

    @vFromQmlInvokable(result=bool)
    @vFromQmlInvokable(QModelIndex, result=bool)
    def canLoadPreviousChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Возвращает True - если используется политика "ручной" загрузки подэлементов и если
        в данный момент можно загрузить предыдущую порцию подэлементов элемента с модельным индексом `parent`,
        иначе - возвращает False.
        """
        return self._canLoadPreviousChildren(parent, Vns.LoadingPolicy.Manually)

    def _canLoadPreviousChildren(self, parent: QModelIndex, policy: Vns.LoadingPolicy) -> bool:
        assert parent.model() is self if parent.isValid() else True
        info = self._getChildrenLoadingInfo(parent)
        if info is None:
            return False
        if policy not in info.policy:
            return False
        if info.state not in (Vns.LoadingState.Error, Vns.LoadingState.Idle):
            return False
        return info.pagination.canLoadPreviousData()

    @vFromQmlInvokable(result=VAbstractAsynchronousAction)
    @vFromQmlInvokable(QModelIndex, result=VAbstractAsynchronousAction)
    def loadPreviousChildren(self, parent: QModelIndex = QModelIndex()) -> VAbstractAsynchronousAction:
        """Запускает асинхронную загрузку предыдущей порции подэлементов из элемента с модельным индексом `parent`.

        Возвращает экземпляр действия :class:`VAbstractAsynchronousAction`.

        Данный метод поддерживается только, если пагинация поддерживает последовательную загрузку порций подэлементов
        с заменой ранее загруженных порций на новые.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что его вызов разрешен.

            Это можно сделать, например, с помощью метода :func:`canLoadPreviousChildren()` с соответствующим аргументом,
            если используется политика "ручной" загрузки подэлементов  (т.е. `Vns.LoadingPolicy.Manually`).

        ..warning::
            Если родителем действия будет являться данная модель, то действие будет удалено сразу после завершения,
            иначе ответственность по его удалению будет лежать на Вас.
        """
        assert self._canLoadPreviousChildren(parent, Vns.LoadingPolicy.Automatically) \
               or self._canLoadPreviousChildren(parent, Vns.LoadingPolicy.Manually)
        info = self._getChildrenLoadingInfo(parent)
        assert info
        info.pagination._requestToLoadingPreviousDataPart()
        return self._loadChildren(parent)

    def _loadChildren(self, parent: QModelIndex) -> VNetworkModelAction:
        """Запускает асинхронную загрузку подэлементов из элемента с модельным индексом `parent`.

        Возвращает экземпляр действия :class:`VNetworkModelAction`.

        .. warning::
            Перед вызовом данного метода необходимо сначала убедиться, что его вызов разрешен, затем подготовить
            все необходимые параметры, такие как пагинация и прочие, и только затем уже вызвать данный метод.

        ..warning::
            Если родителем действия будет являться данная модель, то действие будет удалено сразу после завершения,
            иначе ответственность по его удалению будет лежать на Вас.

        ..note::
            Если действие станет недействительным (то есть если до завершения действия будет удален элемент с индексом
            `parent`), то сетевой запрос действия будет отменен.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        assert parent.model() is self if parent.isValid() else True

        info = self._getChildrenLoadingInfo(parent)

        assert info is not None
        assert info.policy != Vns.LoadingPolicy.DoNotLoad
        assert info.state in (Vns.LoadingState.Error, Vns.LoadingState.Idle)
        assert info.pagination.getType() != Vns.PaginationType.Nothing

        self._setChildrenLoadingState(Vns.LoadingState.Loading, parent, info)
        self.childrenLoadingStarted.emit(parent)

        reply = self._requestToLoadingChildren(parent)
        assert reply  # Проверяем, не забыли ли переопределить метод `self._requestToLoadingChildren(parent)`.
        assert reply.isRunning()
        action = VNetworkModelAction(
                model=self,
                index=parent,
                reply=reply,
                type=Vns.ActionType.LoadingChildren,
                parent=self)

        if self._handleNotAccessibleNetwork(action):
            self._setChildrenLoadingState(Vns.LoadingState.Error, parent, info)
            self.childrenLoadingFinished.emit(parent)
            if info.inReloading:
                info.inReloading = False
            return action

        # action.finished.connect(lambda: self.deleteActionLater(action))
        action.invalidated.connect(action.replyAbort)
        action.replyFinished.connect(self._finishLoadingChildren)
        self._registerAction(action)
        return action

    def _requestToLoadingChildren(self, parent: QModelIndex) -> QNetworkReply or None:
        """Запрашивает данные подэлементов из элемента с модельным индексом `parent`.

        Возвращает ответ в виде экземпляра :class:`QNetworkReply` или None, если данные запросить нельзя.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `parent`, возвращает None.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.

        :param parent: Модельный индекс элемента, из которого загружаются подэлементы.
        :rtype: QNetworkReply or None
        """
        raise NotImplementedError()

    def _finishLoadingChildren(self):
        """Завершает асинхронную загрузку подэлементов.
        (Завершает действие :class:`VNetworkModelAction`, подключенное к этому слоту).
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        action = self.sender()
        assert isinstance(action, VNetworkModelAction)

        assert action.isRunning()
        assert action.getModel() is self
        assert action._reply().isFinished() \
            if action._reply() and action._reply().manager().networkAccessible() == action._reply().manager().Accessible \
            else True  # Такое мудреное утверждение из-за багов в Qt при отключенной сети!
        assert action.getType() == Vns.ActionType.LoadingChildren

        if not action.isValid():
            # Если элемент, из которого загружались подэлементы, был удален.
            self._unregisterAction(action)
            self.deleteActionLater(action)
            return

        parent = action.getIndex()
        assert parent.model() is self if parent.isValid() else True

        info = self._getChildrenLoadingInfo(parent)

        assert info is not None
        assert info.state == Vns.LoadingState.Loading
        # Может быть такая ситуация, когда запустили загрузку, поменяли политику загрузки и пришел ответ по загрузке...
        # assert info.policy() != Vns.LoadingPolicy.DoNotLoad

        if not self._handleNetworkReplyError(action):
            pagination = info.pagination

            if info.inReloading:
                pagination._resetWhenReloadingData()
                self._removeChildren(parent)
            elif pagination.mustRemoveLoadedDataWhenLoadingNewData():
                self._removeChildren(parent)

            if self._appendChildren(parent, action):
                if pagination._updateAfterLoadingData(action):
                    self._setChildrenLoadingState(Vns.LoadingState.Idle, parent, info)
                else:
                    self._removeChildren(parent)
                    pagination._resetWhenReloadingData()

                    # TODO: Можно ли сменить тип ошибки на более подходящий?
                    errorType = Vns.ErrorType.UnknownError
                    informativeText = QCoreApplication.translate("VAbstractNetworkDataModelMixin",
                            "Не удалось обновить пагинацию после загрузки подэлементов.")
                    detailedText = ""
                    action.setError(errorType, informativeText, detailedText)
                    self._setError(errorType, informativeText, detailedText, parent)

                    self._setChildrenLoadingState(Vns.LoadingState.Error, parent, info)
            else:
                self._removeChildren(parent)
                pagination._resetWhenReloadingData()

                # TODO: Можно ли сменить тип ошибки на более подходящий?
                errorType = Vns.ErrorType.UnknownError
                informativeText = QCoreApplication.translate("VAbstractNetworkDataModelMixin",
                        "Не удалось из загруженных данных создать подэлементы и вставить их в модель после их загрузки.")
                detailedText = ""
                action.setError(errorType, informativeText, detailedText)
                self._setError(errorType, informativeText, detailedText, parent)

                self._setChildrenLoadingState(Vns.LoadingState.Error, parent, info)
        else:
            self._setChildrenLoadingState(Vns.LoadingState.Error, parent, info)

        self.childrenLoadingFinished.emit(parent)
        if info.inReloading:
            info.inReloading = False
        self._unregisterAction(action)
        action.setFinished()
        self.deleteActionLater(action)

    # TODO: Модельный индекс нужно убрать из аргументов метода, так как его легко получить из аргумента действия!
    def _appendChildren(self, parent: QModelIndex, action: VNetworkModelAction) -> bool:
        """Создает элементы, используя данные из действия `action`, и добавляет их в качестве подэлементов
        в элемент с модельным индексом `parent`.

        Возвращает True - если создание и вставка завершились успешно, иначе - возвращает False.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _removeChildren(self, parent: QModelIndex):
        """Удаляет загруженные подэлементы элемента с модельным индексом `parent`.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    # TODO: Доделать метод.
    # def _resetChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
    #     """Сбрасывает подэлементы элемента с модельным индексом `parent` в первоначальное незагруженное состояние.
    #
    #     Возвращает True - если сброс был успешным, False - иначе.
    #     """
    #     assert parent.model() is self if parent.isValid() else True
    #     # if not self.childrenAreLoadedSeparately(parent):
    #     #     return False
    #     info = self._getChildrenLoadingInfo(parent)
    #     if info is None:
    #         return False
    #     info.pagination()._resetAll()
    #     info.resetInReloading()
    #     info.resetError()
    #     self._unsubscribeFromChildrenUpdateNotifications(parent, info)
    #     self._resetChildrenLoadingState(parent, info)
    #     self._removeChildren(parent)
    #     return True

    # ==== override QAbstractItemModel methods ====

    # TODO: Перенести в наследников!
    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Переопределяет соответствующий родительский метод."""
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        if self.childrenAreLoadedSeparately(parent):
            return True
        return super().hasChildren(parent)

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """Переопределяет соответствующий родительский метод.

        Возвращает True - если в данный момент можно запустить АВТОМАТИЧЕСКУЮ загрузку следующей порции подэлементов
        из элемента с модельным индексом `parent`, иначе - возвращает False.

        .. note::
            Данный метод автоматически вызывается в представлениях, например, в :class:`PyQt5.QtCore.QAbstractItemView`.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        return self._canLoadNextChildren(parent, Vns.LoadingPolicy.Automatically)

    def fetchMore(self, parent: QModelIndex):
        """Переопределяет соответствующий родительский метод.

        Запускает АВТОМАТИЧЕСКУЮ асинхронную загрузку следующей порции подэлементов из элемента с модельным индексом
        `parent`.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что вызов метода :func:`canFetchMore()` возвращает True.

        .. note::
            Данный метод автоматически вызывается в представлениях, например, в :class:`PyQt5.QtCore.QAbstractItemView`.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        self.loadNextChildren(parent)

    # def setData(self, index: QModelIndex, value, role: int = None) -> bool:
    #     """Переопределяет соответствующий родительский метод.
    #     setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool.
    #     """
    #     assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
    #     if not index.isValid() or index.model() is not self:
    #         return False
    #     # if role in (Qt.DisplayRole, Qt.EditRole):
    #     #     raise NotImplementedError("Действия для этой роли должны переопределить наследники!")  # TODO: !!!
    #     if role >= VItemDataRole.First:
    #         raise NotImplementedError("Для этой роли необходимо использовать метод `sendData()`!")  # TODO: !!!
    #         # Для этих ролей наследники должны сделать сетевой запрос!
    #         # return False
    #     return super().setData(index, value, role)

    # def sendData(self, index: QModelIndex, value, role=None) -> VAbstractAsynchronousAction:
    #     """Запускает асинхронное изменение данных по сети в удаленном хранилище.
    #
    #     sendData(self, index: QModelIndex, value: dict) -> VAbstractAsynchronousAction.
    #     sendData(self, index: QModelIndex, value: Any, role: int) -> VAbstractAsynchronousAction.
    #     sendData(self, index: QModelIndex, value: Any, role: str) -> VAbstractAsynchronousAction.
    #     sendData(self, index: QModelIndex, value: Any, role: list[str]) -> VAbstractAsynchronousAction.
    #
    #     По умолчанию ничего не делает и возвращает действие, которое сразу испустит сигнал завершения с ошибкой.
    #     """
    #     assert isinstance(index, QModelIndex)  # Это только чтобы хоть как-то использовать аргумент.
    #     assert isinstance(value, object)  # Это только чтобы хоть как-то использовать аргумент.
    #     assert isinstance(role, object)  # Это только чтобы хоть как-то использовать аргумент.
    #     return self._createAction()

    # ==== waiting for load methods ====

    # TODO: В этом методе еще дофига нерассмотренных ситуаций, когда надо прерывать ожидание!
    def _waitForCanLoadChildren(self, canLoadChildren: Callable[[QModelIndex], bool],
            parent: QModelIndex = QModelIndex(), timeout: int = -1):
        """Если в текущий момент метод проверки доступности загрузки `canLoadChildren` с аргументом `parent`
        возвращает False, то блокирует вызывающий метод на время, пока `canLoadChildren` не вернет True или
        пока не истечет `timeout` миллисекунд.
        Если `timeout` меньше 0 (по умолчанию), то по таймеру блокировка отменяться не будет.
        Если загрузка подэлементов не поддерживается из элемента с индексом `parent`, то метод не блокируется.

        :param canLoadChildren: Метод (функция) проверки доступности загрузки подэлементов,
                принимающая один аргумент с типом :class:`QModelIndex` и возвращающая значение с типом :class:`bool`.
        :param parent: Модельный индекс элемента.
        :param timeout: Максимальное количество времени (в миллисекундах), на которое блокируется вызывающий метод.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        assert parent.model() is self if parent.isValid() else True
        if not self.childrenAreLoadedSeparately(parent):
            return
        if canLoadChildren(parent):
            return

        persistentParent = QPersistentModelIndex(parent)
        eventLoop = QEventLoop()
        timer = QTimer()

        def handleModelAboutToBeReset():
            timer.stop()
            eventLoop.quit()

        def handleColumnsAboutToBeRemoved(parent: QModelIndex, first: int, last: int):
            if isDescendant(QModelIndex(persistentParent), parent, 0, self.rowCount(parent) - 1, first, last, True):
                timer.stop()
                eventLoop.quit()

        def handleRowsAboutToBeRemoved(parent: QModelIndex, first: int, last: int):
            if isDescendant(QModelIndex(persistentParent), parent, first, last, 0, self.columnCount(parent) - 1, True):
                timer.stop()
                eventLoop.quit()

        def quitIfCanLoadChildren(parent: QModelIndex):
            if parent == QModelIndex(persistentParent):
                if canLoadChildren(parent):
                    timer.stop()
                    eventLoop.quit()

        if persistentParent.isValid():
            self.modelAboutToBeReset.connect(handleModelAboutToBeReset)
            self.columnsAboutToBeRemove.connect(handleColumnsAboutToBeRemoved)
            self.rowsAboutToBeRemoved.connect(handleRowsAboutToBeRemoved)

        self._childrenPaginationChanged.connect(quitIfCanLoadChildren)
        self.childrenLoadingPolicyChanged.connect(quitIfCanLoadChildren)
        self.childrenLoadingStateChanged.connect(quitIfCanLoadChildren)
        if timeout >= 0:
            timer.setInterval(timeout)
            timer.setSingleShot(True)
            timer.timeout.connect(eventLoop.quit)
            timer.start()
        eventLoop.exec()
        self._childrenPaginationChanged.disconnect(quitIfCanLoadChildren)
        self.childrenLoadingPolicyChanged.disconnect(quitIfCanLoadChildren)
        self.childrenLoadingStateChanged.disconnect(quitIfCanLoadChildren)

        if persistentParent.isValid():
            self.modelAboutToBeReset.disconnect(handleModelAboutToBeReset)
            self.columnsAboutToBeRemove.disconnect(handleColumnsAboutToBeRemoved)
            self.rowsAboutToBeRemoved.disconnect(handleRowsAboutToBeRemoved)

    @vFromQmlInvokable()
    @vFromQmlInvokable(QModelIndex)
    @vFromQmlInvokable(QModelIndex, int)
    @vFromQmlInvokable(int)
    def waitForCanReloadChildren(self, parent: QModelIndex = QModelIndex(), timeout: int = -1):
        """Если в текущий момент запрещено перезагружать подэлементы элемента с индексом `parent`, то блокирует
        вызывающий метод на время, пока запрещено перезагружать подэлементы или пока не истечет `timeout` миллисекунд.
        Если `timeout` меньше 0 (по умолчанию), то по таймеру блокировка отменяться не будет.
        Если загрузка подэлементов не поддерживается из элемента с индексом `parent`, то метод не блокируется.
        """
        self._waitForCanLoadChildren(self.canReloadChildren, parent, timeout)

    @vFromQmlInvokable()
    @vFromQmlInvokable(QModelIndex)
    @vFromQmlInvokable(QModelIndex, int)
    @vFromQmlInvokable(int)
    def waitForCanLoadNextChildren(self, parent: QModelIndex = QModelIndex(), timeout: int = -1):
        """Если в текущий момент запрещено загружать следующую порцию подэлементов элемента с индексом `parent`, то блокирует
        вызывающий метод на время, пока запрещено загружать подэлементы или пока не истечет `timeout` миллисекунд.
        Если `timeout` меньше 0 (по умолчанию), то по таймеру блокировка отменяться не будет.
        Если загрузка подэлементов не поддерживается из элемента с индексом `parent`, то метод не блокируется.
        """
        self._waitForCanLoadChildren(self.canLoadNextChildren, parent, timeout)

    @vFromQmlInvokable()
    @vFromQmlInvokable(QModelIndex)
    @vFromQmlInvokable(QModelIndex, int)
    @vFromQmlInvokable(int)
    def waitForCanLoadPreviousChildren(self, parent: QModelIndex = QModelIndex(), timeout: int = -1):
        """Если в текущий момент запрещено загружать предыдущую порцию подэлементов элемента с индексом `parent`, то блокирует
        вызывающий метод на время, пока запрещено загружать подэлементы или пока не истечет `timeout` миллисекунд.
        Если `timeout` меньше 0 (по умолчанию), то по таймеру блокировка отменяться не будет.
        Если загрузка подэлементов не поддерживается из элемента с индексом `parent`, то метод не блокируется.
        """
        self._waitForCanLoadChildren(self.canLoadPreviousChildren, parent, timeout)

    # ============================
    # ==== loading of details ====
    # ============================

    def _getDetailsLoadingInfo(self, index: QModelIndex) -> VDetailsLoadingInfo or None:
        """Возвращает контейнер со вспомогательной (служебной) информацией о загрузке подробных данных об элементе
        с модельным индексом `index`.

        .. note::
            Если загрузка подробных данных не поддерживается для элемента с модельным индексом `index`, возвращает None.

        Именно этот метод определяет, поддерживается ли загрузка подробных данных для конкретного элемента.

        .. warning::
            Базовая реализация всегда возвращает None.
            Наследники класса должны переопределить этот метод, чтобы позволить загружать подробные данные об элементах.
        """
        assert isinstance(index, QModelIndex)  # Это чтобы хоть как-то использовать аргумент.
        return None

    @vFromQmlInvokable(QModelIndex, result=bool)
    def detailsAreLoadedSeparately(self, index: QModelIndex) -> bool:
        # TODO: Переименовать на detailsCanLoadedSeparately?
        """Возвращает True - если поддерживается загрузка подробных данных для элемента с модельным индексом `index`,
        иначе - возвращает False.

        (Возвращает True - если подробные данные элемента с индексом `index` загружаются отдельно, False - иначе.)

        .. note::
            Базовая реализация вызывает метод :func:`_getDetailsLoadingInfo()`.
            Вы можете переопределить это для ускорения работы данного метода.
        """
        return self._getDetailsLoadingInfo(index) is not None

    # ==== detailsLoadingState ====

    detailsLoadingStateChanged = pyqtSignal(QModelIndex, arguments=['index'])
    """Сигнал об изменении состояния загрузки подробных данных элемента.

    :param QModelIndex index: Модельный индекс элемента.
    """

    @vFromQmlInvokable(QModelIndex, result=int)
    def detailsLoadingState(self, index: QModelIndex) -> Vns.LoadingState:
        """Возвращает состояние загрузки подробных данных для элемента с модельным индексом `index`.

        .. note::
            Если загрузка подробных данных не поддерживается для элемента с модельным индексом `index`,
            возвращает `Vns.LoadingState.Unknown`.
        """
        assert index.model() is self if index.isValid() else True
        info = self._getDetailsLoadingInfo(index)
        # if info is None:
        #     return Vns.LoadingState.Unknown
        # return info.state()
        return info.state if info else Vns.LoadingState.Unknown

    def _setDetailsLoadingState(self, state: Vns.LoadingState, index: QModelIndex,
            info: VDetailsLoadingInfo = None) -> bool:
        """Устанавливает состояние `state` загрузки подробных данных для элемента с модельным индексом `index`
        и информацией `info` о загрузке подробных данных.
        Если информация `info` не указана, то она будет получена из элемента с индексом `index`.

        Возвращает True - если состояние загрузки было установлено успешно, False - иначе.
        """
        assert index.model() is self if index.isValid() else True
        if info is None:
            info = self._getDetailsLoadingInfo(index)
            if info is None:
                return False
        assert info is self._getDetailsLoadingInfo(index)
        if state != info.state:
            info.state = state
            self.detailsLoadingStateChanged.emit(index)
        return True

    # def _resetDetailsLoadingState(self, index: QModelIndex, info: VDetailsLoadingInfo = None) -> bool:
    #     """Сбрасывает состояние загрузки подробных данных для элемента с модельным индексом `index`
    #     и информацией `info` о загрузке подробных данных на значение по-умолчанию.
    #     Если информация `info` не указана, то она будет получена из элемента с индексом `index`.
    #
    #     Возвращает True - если состояние загрузки было сброшено успешно, False - иначе.
    #     """
    #     assert index.model() is self if index.isValid() else True
    #     if info is None:
    #         info = self._getDetailsLoadingInfo(index)
    #         if info is None:
    #             return False
    #     assert info is self._getDetailsLoadingInfo(index)
    #     if info.resetState():  # TODO: На какое значение тут сбрасывать?
    #         self.detailsLoadingStateChanged.emit(index)
    #     return True

    @vFromQmlInvokable(QModelIndex, result=bool)
    def detailsLoadingIsInIdleState(self, index: QModelIndex) -> bool:
        """Возвращает True - если загрузка подробных данных элемента с индексом `index` находится в состоянии покоя,
        иначе - возвращает False."""
        return self.detailsLoadingState(index) == Vns.LoadingState.Idle

    @vFromQmlInvokable(QModelIndex, result=bool)
    def detailsLoadingIsInLoadingState(self, index: QModelIndex) -> bool:
        """Возвращает True - если подробные данные элемента с индексом `index` находятся в состоянии загрузки,
        иначе - возвращает False."""
        return self.detailsLoadingState(index) == Vns.LoadingState.Loading

    @vFromQmlInvokable(QModelIndex, result=bool)
    def detailsLoadingIsInErrorState(self, index: QModelIndex) -> bool:
        """Возвращает True - если загрузка подробных данных элемента с индексом `index` находится в состоянии ошибки,
        иначе - возвращает False."""
        return self.detailsLoadingState(index) == Vns.LoadingState.Error

    @vFromQmlInvokable(QModelIndex, result=bool)
    def detailsLoadingIsInUnknownState(self, index: QModelIndex) -> bool:
        """Возвращает True - если загрузка подробных данных элемента с индексом `index` находится в неизвестном
        состоянии, иначе - возвращает False."""
        return self.detailsLoadingState(index) == Vns.LoadingState.Unknown

    # ==== loading of details methods ====

    @vFromQmlInvokable(QModelIndex, result=bool)
    def hasLoadedDetails(self, index: QModelIndex) -> bool:
        # TODO: Название метода не очень удачное, надо бы переименоватьна то, что лучше отображает суть метода!
        """Возвращает True - если в элементе с модельным индексом `index` имеются уже загруженные подробные данные,
        иначе - возвращает False.

        # TODO: Поправить документацию:
        То есть загружены ли уже подробные данные об элементе.

        .. note::
            Если загрузка подробных данных не поддерживается для элемента с модельным индексом `index`, возвращает False.
        """
        assert index.model() is self if index.isValid() else True
        info = self._getDetailsLoadingInfo(index)
        if info is None:
            return False
        return info.loaded

    detailsLoadingStarted = pyqtSignal(QModelIndex, arguments=['index'])
    """Сигнал о начале загрузки подробных данных об элементе.

    :param QModelIndex index: Модельный индекс элемента.
    """

    detailsLoadingFinished = pyqtSignal(QModelIndex, arguments=['index'])
    """Сигнал о завершении загрузки подробных данных об элементе.

    :param QModelIndex index: Модельный индекс элемента.
    """

    @vFromQmlInvokable(QModelIndex, result=bool)
    def canReloadDetails(self, index: QModelIndex) -> bool:
        """Возвращает True - если в данный момент можно перезагрузить подробные данные для элемента с индексом `index`
        (перезагрузить, если подробные данные уже загружены, или загрузить, если они еще не загружены),
        иначе - возвращает False.
        """
        assert index.model() is self if index.isValid() else True
        info = self._getDetailsLoadingInfo(index)
        if info is None:
            return False
        if info.state not in (Vns.LoadingState.Error, Vns.LoadingState.Idle):
            return False
        return True

    @vFromQmlInvokable(QModelIndex, result=VAbstractAsynchronousAction)
    def reloadDetails(self, index: QModelIndex) -> VAbstractAsynchronousAction:
        """Запускает асинхронную перезагрузку подробных данных для элемента с модельным индексом `index`.
        (Перезагрузку, если подробные данные уже загружены, или загрузку, если они еще не загружены.)

        Возвращает экземпляр действия :class:`VAbstractAsynchronousAction`.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что метод :func:`canReloadDetails()` возвращает True.

        ..warning::
            Если родителем действия будет являться данная модель, то действие будет удалено сразу после завершения,
            иначе ответственность по его удалению будет лежать на Вас.

        ..note::
            Если действие станет недействительным (то есть если до завершения действия будет удален элемент с индексом
            `index`), то сетевой запрос действия будет отменен.
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        assert index.model() is self if index.isValid() else True
        assert self.canReloadDetails(index)

        info = self._getDetailsLoadingInfo(index)
        assert info is not None
        assert info.state in (Vns.LoadingState.Error, Vns.LoadingState.Idle)

        self._setDetailsLoadingState(Vns.LoadingState.Loading, index, info)
        self.detailsLoadingStarted.emit(index)

        reply = self._requestToLoadingDetails(index)
        assert reply  # Проверяем, не забыли ли переопределить метод `self._requestToLoadingDetails(index)`.
        assert reply.isRunning()
        action = VNetworkModelAction(
                model=self,
                index=index,
                reply=reply,
                type=Vns.ActionType.LoadingDetails,
                parent=self)

        if self._handleNotAccessibleNetwork(action):
            self._setDetailsLoadingState(Vns.LoadingState.Error, index, info)
            self.detailsLoadingFinished.emit(index)
            return action

        # action.finished.connect(lambda: self.deleteActionLater(action))
        action.invalidated.connect(action.replyAbort)
        action.replyFinished.connect(self._finishLoadingDetails)
        self._registerAction(action)
        return action

    def _requestToLoadingDetails(self, index: QModelIndex) -> QNetworkReply or None:
        """Запрашивает подробные данные для элемента с модельным индексом `index`.

        Возвращает ответ в виде экземпляра :class:`QNetworkReply` или None, если данные запросить нельзя.

        .. note::
            Если загрузка подробных данных не поддерживается для элемента с модельным индексом `index`, возвращает None.

        .. warning::
            Базовая реализация ничего не делает и всегда возвращает None.
            Наследники класса должны переопределить этот метод, чтобы позволить загружать подробные данные об элементах.

        :param index: Модельный индекс элемента, для которого загружаются подробные данные.
        :rtype: QNetworkReply or None
        """
        assert isinstance(index, QModelIndex)  # Это чтобы хоть как-то использовать аргумент.
        assert self._getDetailsLoadingInfo(index) is None  # Проверяем, не забыли ли переопределить этот метод.
        return None

    def _finishLoadingDetails(self):
        """Завершает асинхронную загрузку подробных данных об элементе.
        (Завершает действие :class:`VNetworkModelAction`, подключенное к этому слоту).
        """
        assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
        action = self.sender()
        assert isinstance(action, VNetworkModelAction)

        assert action.isRunning()
        assert action.getModel() is self
        assert action._reply().isFinished() \
            if action._reply() and action._reply().manager().networkAccessible() == action._reply().manager().Accessible \
            else True  # Такое мудреное утверждение из-за багов в Qt при отключенной сети!
        assert action.getType() == Vns.ActionType.LoadingDetails

        if not action.isValid():
            # Если элемент, для которого загружались подробные данные, был удален.
            self._unregisterAction(action)
            self.deleteActionLater(action)
            return

        index = action.getIndex()
        assert index.model() is self if index.isValid() else True

        info = self._getDetailsLoadingInfo(index)

        assert info is not None
        assert info.state == Vns.LoadingState.Loading

        if not self._handleNetworkReplyError(action):
            if self._updateDetails(action):
                info.loaded = True
                self._setDetailsLoadingState(Vns.LoadingState.Idle, index, info)
            else:
                # TODO: Можно ли сменить тип ошибки на более подходящий?
                errorType = Vns.ErrorType.UnknownError
                informativeText = QCoreApplication.translate("VAbstractNetworkDataModelMixin",
                        "Не удалось обновить подробные данные об элементе после их загрузки.")
                detailedText = ""
                action.setError(errorType, informativeText, detailedText)
                self._setError(errorType, informativeText, detailedText, index)

                self._setDetailsLoadingState(Vns.LoadingState.Error, index, info)
        else:
            self._setDetailsLoadingState(Vns.LoadingState.Error, index, info)

        self.detailsLoadingFinished.emit(index)
        self._unregisterAction(action)
        action.setFinished()
        self.deleteActionLater(action)

    def _updateDetails(self, action: VNetworkModelAction) -> bool:
        """Обновляет подробные данные об элементе, используя данные из действия `action`.

        Возвращает True - если обновление завершилось успешно, иначе - возвращает False.

        .. warning::
            Базовая реализация ничего не делает и всегда возвращает False.
            Наследники класса должны переопределить этот метод, чтобы позволить загружать подробные данные об элементах.
        """
        # assert action.getIndex().isValid()  # Впринципе, не стоит ограничивать валидность индекса.
        assert self._getDetailsLoadingInfo(action.getIndex()) is None  # Проверяем, не забыли ли переопределить этот метод.
        return False
