#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
from typing import Any, List, Tuple, Union

from PyQt5.QtCore import (QAbstractItemModel, QByteArray, QEventLoop, QModelIndex, QPersistentModelIndex, QObject,
                          QTimer, pyqtSignal, pyqtSlot)
from PyQt5.QtNetwork import QNetworkReply

from .client import VAbstractNetworkClient
from .namespace import Vns


# TODO: Пока так помечаем то, что должно быть помечено через макрос Q_INVOKABLE.
vFromQmlInvokable = pyqtSlot


class VAbstractAsynchronousAction(QObject):
    """Абстрактное асинхронное действие.

    Определяет публичный интерфейс для асинхронных действий.

    # TODO: Следует разбить описание на 2 раздела: для конечного программиста и для разработчика действия.

    Действие может оставаться актуальным на всем протяжении своего выполнения или же стать неактуальным за это время,
    например, если объект, над которым производилось действие, был удален.

    В случае завершения актуального действия испускается сигнал `finished`.
    (Если наследники будут поддерживать отмену действия, то после её отмены они должны установить тип ошибки,
    соответствующий отмене действия, и испустить сигнал `finished`.)

    После завершения актуального действия, его можно проверить на наличие ошибок с помощью методов
    :func:`isError()` и :func:`errorType()`.
    Текстовое описание ошибки можно получить с помощью методов
    :func:`errorInformativeText()` и :func:`errorDetailedText()`.

    Если во время своего исполнения действие перестало быть актуальным, то испускается сигнал `invalidated`
    без сигнала `finished`.
    """

    invalidated = pyqtSignal()
    """Сигнал об инвалидации действия. С этого момента действие является недействительным/неактуальным."""

    finished = pyqtSignal()
    """Сигнал о завершении действительного/актуального действия."""

    # @vFromQmlInvokable()
    # def deleteLater(self):  # Переопределили только лишь для доступа из QML!
    #     """Переопределяет соответствующий родительский метод."""
    #     super().deleteLater()

    @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Возвращает тип действия.

        .. note:: Стандартные типы смотри в :class:`Vns.ActionType`.
        """
        raise NotImplementedError()

    # TODO: Выяснить, вызовется ли в наследнике его переопределенный метод getType, при обращении к свойству type?!!
    # type = pyqtProperty(type=int, fget=getType, doc="Тип действия.")

    @vFromQmlInvokable(result=bool)
    def isValid(self) -> bool:
        """Возвращает True - если действие действительно, иначе - возвращает False."""
        raise NotImplementedError()

    @vFromQmlInvokable(result=bool)
    def isRunning(self) -> bool:
        """Возвращает True - если действие все еще обрабатывается, иначе - возвращает False."""
        return not self.isFinished()

    @vFromQmlInvokable(result=bool)
    def isFinished(self) -> bool:
        """Возвращает True - если действие было завершено (или прервано/отменено), иначе - возвращает False."""
        raise NotImplementedError()

    @vFromQmlInvokable(result=bool)
    def isError(self) -> bool:
        """Возвращает True - если произошла ошибка, иначе - возвращает False."""
        raise NotImplementedError()

    @vFromQmlInvokable(result=int)
    def errorType(self) -> int:
        """Возвращает тип ошибки.

        .. note:: Стандартные типы смотри в :class:`Vns.ErrorType`.
        """
        raise NotImplementedError()

    @vFromQmlInvokable(result=str)
    def errorInformativeText(self) -> str:
        """Возвращает общеописательный текст ошибки. (Обычно, это текст ошибки ответа на сетевой запрос.)"""
        raise NotImplementedError()

    @vFromQmlInvokable(result=str)
    def errorDetailedText(self) -> str:
        """Возвращает подробный текст ошибки. (Обычно, это тело ответа на сетевой запрос.)"""
        raise NotImplementedError()

    @vFromQmlInvokable()
    def waitForFinishedOrInvalidated(self, timeout: int = -1):
        """Блокирует вызывающий метод на время, пока не будет завершено данное действие,
        или пока не истечет `timeout` миллисекунд.
        Если `timeout` меньше 0 (по умолчанию), то по таймеру блокировка отменяться не будет.
        """
        if self.isFinished():
            return

        event_loop = QEventLoop()
        self.invalidated.connect(event_loop.quit)
        self.finished.connect(event_loop.quit)
        self.destroyed.connect(event_loop.quit)
        if timeout >= 0:
            timer = QTimer()
            timer.setInterval(timeout)
            timer.setSingleShot(True)
            timer.timeout.connect(event_loop.quit)
            # Если блокировка отменится до истечения таймера, то при выходе из метода таймер остановится и уничтожится.
            timer.start()
        event_loop.exec()
        self.invalidated.disconnect(event_loop.quit)
        self.finished.disconnect(event_loop.quit)
        self.destroyed.disconnect(event_loop.quit)  # TODO: Не упадет ли прога здесь, если действие уже удалилось?


class VAsynchronousAction(VAbstractAsynchronousAction):
    """Асинхронное действие.

    Реализует интерфейс абстрактного асинхронного действия и дополняет его публичными методами установки/изменения
    значений, так как является закрытым классом-реализацией, которая не должна быть доступна конечному пользователю.
    """

    def __init__(self, type: int = Vns.ActionType.Custom, parent: QObject = None):
        super().__init__(parent)

        self.__type = type
        self.__isValid = True
        self.__isFinished = False
        self.__errorType = Vns.ErrorType.NoError
        self.__errorInformativeText = ""
        self.__errorDetailedText = ""

        # TODO: Delete me!
        def printError():
            assert self.isValid()
            assert self.isFinished()
            if self.isError():
                print("Action is finished with error:\nerrorInformativeText =", self.errorInformativeText(), "\nerrorDetailedText =", self.errorDetailedText())

        self.finished.connect(printError)

    @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Переопределяет соответствующий родительский метод.

        Возвращает тип действия.

        .. note:: Стандартные типы смотри в :class:`Vns.ActionType`.
        """
        return self.__type

    def setType(self, type: int):
        """Устанавливает тип действия."""
        self.__type = type

    @vFromQmlInvokable(result=bool)
    def isValid(self) -> bool:
        """Переопределяет соответствующий родительский метод.

        Возвращает True - если действие действительно, иначе - возвращает False.
        """
        return self.__isValid

    def setInvalidated(self):
        """Помечает действие недействительным и испускает сигнал `invalidated`."""
        assert not self.__isFinished  # Недействительным может стать только незавершенное действие.
        assert self.__isValid  # Сигнал должен испускаться ровно 1 раз!
        if self.__isValid:
            self.__isValid = False
            self.invalidated.emit()

    # @vFromQmlInvokable(result=bool)
    # def isRunning(self) -> bool:
    #     """Переопределяет соответствующий родительский метод.
    #
    #     Возвращает True - если действие все еще обрабатывается, иначе - возвращает False.
    #     """
    #     return not self.__isFinished

    @vFromQmlInvokable(result=bool)
    def isFinished(self) -> bool:
        """Переопределяет соответствующий родительский метод.

        Возвращает True - если действие было завершено (или прервано/отменено), иначе - возвращает False.
        """
        return self.__isFinished

    # TODO: Можно добавить параметр, определяющий отложенность установки завершенности - сразу или при следующем круге цикла событий...
    def setFinished(self):
        """Помечает действие завершенным и испускает сигнал `finished`."""
        assert self.__isValid  # Завершенным может стать только действительное действие.
        assert not self.__isFinished  # Сигнал должен испускаться ровно 1 раз!
        if not self.__isFinished:
            self.__isFinished = True
            self.finished.emit()

    @vFromQmlInvokable(result=bool)
    def isError(self) -> bool:
        """Переопределяет соответствующий родительский метод.

        Возвращает True - если произошла ошибка, иначе - возвращает False.
        """
        return self.__errorType != Vns.ErrorType.NoError

    @vFromQmlInvokable(result=int)
    def errorType(self) -> int:
        """Переопределяет соответствующий родительский метод.

        Возвращает тип ошибки.

        .. note:: Стандартные типы смотри в :class:`Vns.ErrorType`.
        """
        return self.__errorType

    @vFromQmlInvokable(result=str)
    def errorInformativeText(self) -> str:
        """Переопределяет соответствующий родительский метод.

        Возвращает общеописательный текст ошибки. (Обычно, это текст ошибки ответа на сетевой запрос.)
        """
        return self.__errorInformativeText

    @vFromQmlInvokable(result=str)
    def errorDetailedText(self) -> str:
        """Переопределяет соответствующий родительский метод.

        Возвращает подробный текст ошибки. (Обычно, это тело ответа на сетевой запрос.)
        """
        return self.__errorDetailedText

    def setError(self, errorType: int, informativeText: str, detailedText: str = ""):
        """Устанавливает данные об ошибке.

        .. warning:: Но не устанавливает завершенность действия!

        .. note:: Стандартные типы смотри в :class:`Vns.ErrorType`.
        """
        # assert errorType != Vns.ErrorType.NoError
        self.__errorType = errorType
        self.__errorInformativeText = informativeText
        self.__errorDetailedText = detailedText

    # # TODO: Можно добавить параметр, определяющий отложенность установки завершенности - сразу или при следующем круге цикла событий...
    # def _setErrorAndFinished(self, errorType: int, informativeText: str, detailedText: str = ""):
    #     """Устанавливает данные об ошибке, помечает действие завершенным и испускает сигнал `finished`."""
    #     self.setError(errorType, informativeText, detailedText)
    #     self.setFinished()

    # def _resetError(self):
    #     """Сбрасывает данные об ошибке на значения по-умолчанию."""
    #     self.setError(Vns.ErrorType.NoError, "", "")


class VNetworkAction(VAsynchronousAction):
    """Асинхронное сетевое действие, являющееся адаптером для ответа на сетевой запрос :class:`QNetworkReply`.

    Позволяет несколько раз считывать (кэширует) тело ответа на сетевой запрос.

    .. warning:: Никто, кроме данного действия не должен считывать тело ответа на сетевой запрос!

    Берет на себя ответственность за удаление ответа на сетевой запрос.

    .. warning::
        Если действие будет удалено прежде, чем ответ на сетевой запрос испустит сигнал QNetworkReply.finished,
        то ответ на сетевой запрос все равно будет удален, и, значит, сеанс с сервером будет прерван некорректно.
        Как в этом случае завершится обработка запроса - зависит от реализации сервера!
    """

    # TODO: Добавить сигналы-посредники для остальных сигналов QNetworkReply.

    replyErrorOccured = pyqtSignal("QNetworkReply::NetworkError", arguments=['errorCode'])
    """Сигнал об ошибке сетевого ответа :class:`QNetworkReply`.

    :param QNetworkReply.NetworkError errorCode: Код ошибки.
    """

    replyFinished = pyqtSignal()
    """Сигнал о готовности сетевого ответа :class:`QNetworkReply`."""

    replyDownloadProgress = pyqtSignal("qint64, qint64", arguments=['bytesReceived', 'bytesTotal'])
    """Сигнал о прогрессе загрузки сетевого ответа :class:`QNetworkReply`.

    :param int bytesReceived: Количество полученных байтов.
    :param int bytesTotal: Общее количество байтов, которые должны быть получены (если неизвестно, то будет равным -1).
    """

    replyUploadProgress = pyqtSignal("qint64, qint64", arguments=['bytesSent', 'bytesTotal'])
    """Сигнал о прогрессе отправки сетевого запроса (через сетевой ответ :class:`QNetworkReply`).

    :param int bytesSent: Количество отправленных байтов.
    :param int bytesTotal: Общее количество байтов, которые должны быть отправлены (если неизвестно, то будет равным -1).
    """

    def __init__(self, reply: QNetworkReply = None, type: int = Vns.ActionType.Custom, parent: QObject = None):
        super().__init__(type=type, parent=parent)

        self.__replyBody = b""
        self.__reply = reply
        if self.__reply:
            self.__reply.setParent(self)
            # assert self.__reply.isRunning() \
            #     if self.__reply and self.__reply.manager().networkAccessible() == self.__reply.manager().Accessible \
            #     else True  # Такое мудреное утверждение из-за багов в Qt при отключенной сети!
        self._createReplyConnections()

    def _createReplyConnections(self):
        """Соединяет сигналы сетевого ответа со своими сигналами."""
        if self.__reply:
            self.__reply.error.connect(self.replyErrorOccured)
            self.__reply.finished.connect(self.replyFinished)
            self.__reply.downloadProgress.connect(self.replyDownloadProgress)
            self.__reply.uploadProgress.connect(self.replyUploadProgress)

    def _removeReplyConnections(self):
        """Разединяет сигналы сетевого ответа со своими сигналами."""
        if self.__reply:
            self.__reply.error.disconnect(self.replyErrorOccured)
            self.__reply.finished.disconnect(self.replyFinished)
            self.__reply.downloadProgress.disconnect(self.replyDownloadProgress)
            self.__reply.uploadProgress.disconnect(self.replyUploadProgress)

    def _reply(self) -> QNetworkReply:
        """Возвращает экземпляр сетевого ответа :class:`QNetworkReply` или None."""
        return self.__reply

    def setReply(self, value: QNetworkReply):
        """Устанавливает экземпляр сетевого ответа :class:`QNetworkReply`.

        Берет на себя ответственность за его удаление.
        """
        if value is self.__reply:
            return
        assert value.isRunning()
        self._removeReplyConnections()
        if self.__reply and self.__reply.parent() is self:
            self.__reply.deleteLater()
        self.__reply = value
        self.__reply.setParent(self)
        self.__replyBody = b""
        self._createReplyConnections()

    # def setFinished(self):
    #     """Переопределяет соответствующий родительский метод.
    #
    #     Устанавливает завершенность и испускает сигнал `finished`.
    #     """
    #     # Нельзя испускать сигнал, пока не завершен запрос!
    #     # Такое мудреное утверждение из-за багов в Qt при отключенной сети!
    #     assert self.__reply.isFinished() \
    #         if self.__reply and self.__reply.manager().networkAccessible() == self.__reply.manager().Accessible \
    #         else True
    #     super().setFinished()

    def replyBodyRawData(self) -> bytes:
        """Возвращает тело сетевого ответа в бинарном виде.
        Если ответ еще не готов - возвращает пустую байтовую последовательность.
        """
        if not self.__replyBody:
            if self.__reply and self.__reply.isFinished():
                self.__replyBody = bytes(self.__reply.readAll())
        return self.__replyBody

    def replyBodyStringData(self) -> str:
        """Возвращает тело сетевого ответа в виде текста. Если ответ еще не готов - возвращает пустую строку."""
        if self.__reply and self.__reply.isFinished():
            encoding = VAbstractNetworkClient.encodingFrom(self.__reply, default="utf-8")
            return self.replyBodyRawData().decode(encoding)
        return ""

    def replyAbort(self):
        """Если есть экземпляр ответа на сетевой запрос:
        Немедленно прерывает выполнение сетевого запроса и закрывает все сетевые подключения.
        Загрузка уже выполненного запроса также прерывается.
        Затем испускает сигнал завершения ответа на сетевой запрос.
        """
        if self.__reply is None:
            return
        self.__reply.abort()

    def replyAttribute(self, code: int) -> Any:
        """replyAttribute(self, code: QNetworkRequest.Attribute) -> Any."""
        if self.__reply is None:
            return None
        return self.__reply.attribute(code)

    def replyErrorType(self) -> int:
        """replyErrorType(self) -> QNetworkReply.NetworkError."""
        if self.__reply is None:
            return QNetworkReply.UnknownNetworkError
        return self.__reply.error()

    def replyErrorString(self) -> str:
        """replyErrorString(self) -> str."""
        if self.__reply is None:
            return ""
        return self.__reply.errorString()

    # def replyHttpStatusCode(self) -> Any:
    #     """replyHttpStatusCode(self) -> int or None.
    #     Возвращает Http-статус сетевого ответа, если он (статус) есть, иначе - возвращает None.
    #     """
    #     if self.__reply is None:
    #         return None
    #     # return self.__reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    #     return self.__reply.attribute(self.__reply.request().HttpStatusCodeAttribute)

    def replyHeader(self, header: int) -> Any:
        """replyHeader(self, header: QNetworkRequest.KnownHeaders) -> Any."""
        if self.__reply is None:
            return None
        return self.__reply.header(header)

    def replyHasRawHeader(self, headerName: Union[QByteArray, bytes, bytearray]) -> bool:
        """replyHasRawHeader(self, headerName: Union[QByteArray, bytes, bytearray]) -> bool."""
        if self.__reply is None:
            return False
        return self.__reply.hasRawHeader(headerName)

    def replyRawHeader(self, headerName: Union[QByteArray, bytes, bytearray]) -> QByteArray:
        """replyRawHeader(self, headerName: Union[QByteArray, bytes, bytearray]) -> QByteArray."""
        if self.__reply is None:
            return QByteArray()
        return self.__reply.rawHeader(headerName)

    def replyRawHeaderList(self) -> List[QByteArray]:
        """replyRawHeaderList(self) -> List[QByteArray]."""
        if self.__reply is None:
            return []
        return self.__reply.rawHeaderList()

    def replyRawHeaderPairs(self) -> List[Tuple[QByteArray, QByteArray]]:
        """replyRawHeaderPairs(self) -> List[Tuple[QByteArray, QByteArray]]."""
        if self.__reply is None:
            return []
        return self.__reply.rawHeaderPairs()

    def replyContentType(self, default=None):
        """Определяет и возвращает MIME-тип содержимого (со всеми вспомогательными данными, напр., кодировкой)
        из http-заголовка `Content-type` в сетевом ответе.
        Если тип содержимого определить невозможно, возвращает `default`.
        """
        if self.__reply is None:
            return default
        return VAbstractNetworkClient.contentTypeFrom(reply=self.__reply, default=default)

    def replyEncoding(self, default: str = "utf-8") -> str:
        """Определяет и возвращает кодировку содержимого из http-заголовка `Content-type` в сетевом ответе.
        Если кодировку определить невозможно, возвращает `default`.
        """
        if self.__reply is None:
            return default
        return VAbstractNetworkClient.encodingFrom(reply=self.__reply, default=default)


class VNetworkModelAction(VNetworkAction):
    """Асинхронное сетевое действие модели.

    Хранит модельный индекс, указывающий на элемент модели, над которым производится данное действие.
    """

    def __init__(self, model: QAbstractItemModel = None, index: QModelIndex = QModelIndex(),
            reply: QNetworkReply = None, type: int = Vns.ActionType.Custom, parent: QObject = None):
        super().__init__(reply=reply, type=type, parent=parent)

        self.__model = model
        self.__persistentIndex = QPersistentModelIndex(index)

    @vFromQmlInvokable(result=QAbstractItemModel)
    def getModel(self) -> QAbstractItemModel:
        """Возвращает модель, в которой совершается действие."""
        return self.__model

    # model = pyqtProperty(type=QAbstractItemModel, fget=getModel, doc="Модель, в которой совершается действие.")

    def setModel(self, model: QAbstractItemModel):
        """Устанавливает модель, в которой совершается действие."""
        self.__model = model

    @vFromQmlInvokable(result=QModelIndex)
    def getIndex(self) -> QModelIndex:
        """Возвращает индекс элемента, над которым совершается действие."""
        return QModelIndex(self.__persistentIndex)

    # index = pyqtProperty(type=QModelIndex, fget=getIndex, doc="Индекс элемента, над которым совершается действие.")

    def setIndex(self, index: QModelIndex):
        """Устанавливает индекс элемента, над которым совершается действие."""
        self.__persistentIndex = QPersistentModelIndex(index)
