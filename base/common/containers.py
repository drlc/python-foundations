from base.common.adapters.stores.common import StoreConnection, get_db_instance
from base.common.settings import AppSettings
from base.common.utils.logger import Logger


class CtnrApplication:

    singletons = {}

    def provider(self, key):
        def inner():
            if key not in self.singletons:
                raise Exception(f"Singleton {key} not found")
            return self.singletons[key]

        return inner

    def get(self, key):
        return self.provider(key)()

    def init(self, logger: Logger, settings: AppSettings):
        self.singletons[Logger] = logger
        self.singletons[AppSettings] = settings
        self.singletons[StoreConnection] = get_db_instance(
            config=self.get(AppSettings).store_connection,
            parent_logger=self.get(Logger),
        )

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super(CtnrApplication, cls).__new__(cls)
        return cls._instance
