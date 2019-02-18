#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
from PyQt5.QtCore import *
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class VAbstractNetworkClient(QObject):
    """Позволяет приложению отправлять сетевые запросы и получать на них ответы.

    Вся работа с сетью должна быть инкапсулирована в его наследниках.
    """

    @staticmethod
    def contentTypeFrom(reply: QNetworkReply, default=None):
        """Определяет и возвращает MIME-тип содержимого (со всеми вспомогательными данными, напр., кодировкой)
        из http-заголовка `Content-type` в ответе `reply`.
        Если тип содержимого определить невозможно, возвращает `default`.
        """
        assert reply
        contentType = reply.header(QNetworkRequest.ContentTypeHeader)
        if contentType:
            assert isinstance(contentType, str)  # TODO: Delete me!
            return contentType
        return default

    @staticmethod
    def encodingFrom(reply: QNetworkReply, default: str = "utf-8") -> str:
        """Определяет и возвращает кодировку содержимого из http-заголовка `Content-type` в ответе `reply`.
        Если кодировку определить невозможно, возвращает `default`.
        """
        missing = object()
        contentType = VAbstractNetworkClient.contentTypeFrom(reply, missing)

        if contentType is missing:
            return default

        try:
            charset = contentType.split(";")[1]
            assert "charset" in charset
            encoding = charset.split("=")[1]
            return encoding.strip()
        except:
            return default

    @staticmethod
    def waitForFinished(reply: QNetworkReply, timeout: int = -1):
        """Блокирует вызывающий метод на время, пока не будет завершен сетевой ответ `reply` (то есть пока
        не испустится сигнал `reply.finished`), или пока не истечет `timeout` миллисекунд.
        Если `timeout` меньше 0 (по умолчанию), то по данному таймеру блокировка отменяться не будет.
        """
        if reply.isFinished():
            return

        event_loop = QEventLoop()
        reply.finished.connect(event_loop.quit)
        if timeout >= 0:
            timer = QTimer()
            timer.setInterval(timeout)
            timer.setSingleShot(True)
            timer.timeout.connect(event_loop.quit)
            # Если блокировка отменится до истечения таймера, то при выходе из метода таймер остановится и уничтожится.
            timer.start()
        event_loop.exec()
        reply.finished.disconnect(event_loop.quit)

    networkAccessManagerChanged = pyqtSignal(QNetworkAccessManager, arguments=['manager'])
    """Сигнал об изменении менеджера доступа к сети.

    :param QNetworkAccessManager manager: Новый менеджер доступа к сети.
    """

    baseUrlChanged = pyqtSignal(QUrl, arguments=['url'])
    """Сигнал об изменении базового url-а.

    :param QUrl url: Новый базовый url.
    """

    replyFinished = pyqtSignal(QNetworkReply, arguments=['reply'])
    """Сигнал о завершении ответа на сетевой запрос.

    :param QNetworkReply reply: Завершенный сетевой запрос.
    """

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self.__networkAccessManager = QNetworkAccessManager(parent=self)
        self.__baseUrl = QUrl()

    def getNetworkAccessManager(self) -> QNetworkAccessManager:
        """Возвращает менеджер доступа к сети."""
        return self.__networkAccessManager

    def setNetworkAccessManager(self, manager: QNetworkAccessManager):
        """Устанавливает менеджер доступа к сети."""
        assert manager
        if manager is self.__networkAccessManager:
            return
        if self.__networkAccessManager.parent() is self:
            self.__networkAccessManager.deleteLater()
        self.__networkAccessManager = manager
        self.networkAccessManagerChanged.emit(manager)

    networkAccessManager = pyqtProperty(type=QNetworkAccessManager, fget=getNetworkAccessManager,
            fset=setNetworkAccessManager, notify=networkAccessManagerChanged, doc="Менеджер доступа к сети.")

    def getBaseUrl(self) -> QUrl:
        """Возвращает базовый url."""
        return QUrl(self.__baseUrl)

    def setBaseUrl(self, url: QUrl):
        """Устанавливает базовый url."""
        if url == self.__baseUrl:
            return
        self.__baseUrl = QUrl(url)
        self.baseUrlChanged.emit(url)

    baseUrl = pyqtProperty(type=QUrl, fget=getBaseUrl, fset=setBaseUrl, notify=baseUrlChanged, doc="Базовый url.")

    def _connectReplySignals(self, reply: QNetworkReply):
        """Соединяет сигналы ответа с сигналами клиента."""
        reply.finished.connect(lambda: self.replyFinished.emit(reply))
        # TODO: Добавить сюда подключение остальных сигналов.

    def _get(self, request: QNetworkRequest) -> QNetworkReply:
        """Запускает отправку GET-запроса и возвращает ответ :class:`QNetworkReply` на него."""
        reply = self.__networkAccessManager.get(request)
        self._connectReplySignals(reply)
        return reply

    def _head(self, request: QNetworkRequest) -> QNetworkReply:
        """Запускает отправку HEAD-запроса и возвращает ответ :class:`QNetworkReply` на него."""
        reply = self.__networkAccessManager.head(request)
        self._connectReplySignals(reply)
        return reply

    def _post(self, request: QNetworkRequest, data=None) -> QNetworkReply:
        """Запускает отправку POST-запроса и возвращает ответ :class:`QNetworkReply` на него.

        _post(self, request: QNetworkRequest) -> QNetworkReply.
        _post(self, request: QNetworkRequest, data: bytes) -> QNetworkReply.
        _post(self, request: QNetworkRequest, data: bytearray) -> QNetworkReply.
        _post(self, request: QNetworkRequest, data: QByteArray) -> QNetworkReply.
        _post(self, request: QNetworkRequest, data: QIODevice) -> QNetworkReply.
        _post(self, request: QNetworkRequest, data: QHttpMultiPart) -> QNetworkReply.
        """
        if data is not None:
            reply = self.__networkAccessManager.post(request, data)
        else:
            reply = self.__networkAccessManager.sendCustomRequest(request, b"POST")
        self._connectReplySignals(reply)
        return reply

    def _put(self, request: QNetworkRequest, data=None) -> QNetworkReply:
        """Запускает отправку PUT-запроса и возвращает ответ :class:`QNetworkReply` на него.

        _put(self, request: QNetworkRequest) -> QNetworkReply.
        _put(self, request: QNetworkRequest, data: bytes) -> QNetworkReply.
        _put(self, request: QNetworkRequest, data: bytearray) -> QNetworkReply.
        _put(self, request: QNetworkRequest, data: QByteArray) -> QNetworkReply.
        _put(self, request: QNetworkRequest, data: QIODevice) -> QNetworkReply.
        _put(self, request: QNetworkRequest, data: QHttpMultiPart) -> QNetworkReply.
        """
        if data is not None:
            reply = self.__networkAccessManager.put(request, data)
        else:
            reply = self.__networkAccessManager.sendCustomRequest(request, b"PUT")
        self._connectReplySignals(reply)
        return reply

    def _delete(self, request: QNetworkRequest, data=None) -> QNetworkReply:
        """Запускает отправку DELETE-запроса и возвращает ответ :class:`QNetworkReply` на него.

        _delete(self, request: QNetworkRequest) -> QNetworkReply.
        _delete(self, request: QNetworkRequest, data: bytes) -> QNetworkReply.
        _delete(self, request: QNetworkRequest, data: bytearray) -> QNetworkReply.
        _delete(self, request: QNetworkRequest, data: QByteArray) -> QNetworkReply.
        _delete(self, request: QNetworkRequest, data: QIODevice) -> QNetworkReply.
        _delete(self, request: QNetworkRequest, data: QHttpMultiPart) -> QNetworkReply.
        """
        if data is not None:
            reply = self.__networkAccessManager.deleteResource(request)
        else:
            reply = self.__networkAccessManager.sendCustomRequest(request, b"DELETE")
        self._connectReplySignals(reply)
        return reply

    def _sendCustomRequest(self, request: QNetworkRequest, verb: bytes, data=None) -> QNetworkReply:
        """Запускает отправку пользовательского запроса и возвращает ответ :class:`QNetworkReply` на него.

        _sendCustomRequest(self, request: QNetworkRequest, verb: bytes) -> QNetworkReply.
        _sendCustomRequest(self, request: QNetworkRequest, verb: bytes, data: bytes) -> QNetworkReply.
        _sendCustomRequest(self, request: QNetworkRequest, verb: bytes, data: bytearray) -> QNetworkReply.
        _sendCustomRequest(self, request: QNetworkRequest, verb: bytes, data: QByteArray) -> QNetworkReply.
        _sendCustomRequest(self, request: QNetworkRequest, verb: bytes, data: QIODevice) -> QNetworkReply.
        _sendCustomRequest(self, request: QNetworkRequest, verb: bytes, data: QHttpMultiPart) -> QNetworkReply.
        """
        reply = self.__networkAccessManager.sendCustomRequest(request, verb, data)
        self._connectReplySignals(reply)
        return reply
