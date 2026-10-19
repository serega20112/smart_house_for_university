"""Providers describing every dependency of the application.

The graph is declared here and nowhere else. Each provider owns one slice of it
and every factory names its collaborators by type, so a missing dependency is a
build error naming a type instead of an ``AttributeError`` at the first request.

Scope follows the lifetime of the thing rather than the convenience of the
caller. The engine, the Redis connection, the HTTP clients, the board transport,
the adapters and the application services live as long as the process. The use
cases are request scoped: they hold no state, and a fresh set per request keeps a
unit of work from being shared between two callers. The background worker enters
the request scope once per job through the Dishka integration for ARQ, which is
why the same providers serve both processes.

Two seams close the cycles this graph really has. The audio of a board reaches
the voice pipeline, which needs the microphone port of the very connection that
owns the audio sink; and announcing a board needs the onboarding service, which
needs a gateway over that same connection. Both are injected as forwardable
callables that resolve their target from the container when it is first needed,
never as an object wired up by hand.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
from dishka import AsyncContainer, Provider, Scope, alias, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.application.dto.esp import AnnounceBoardCommand
from backend.application.handlers.climate import RunCapabilityHandler, SetClimateTargetHandler
from backend.application.handlers.device_switching import SwitchAllHandler, SwitchDeviceHandler
from backend.application.handlers.home_state import (
    DescribeHomeHandler,
    ReadHumidityHandler,
    ReadTemperatureHandler,
)
from backend.application.handlers.scenarios import CancelScenarioHandler, ScheduleScenarioHandler
from backend.application.ports.boards import (
    BoardGateway,
    BoardReport,
    MicrophonePort,
    MicrophoneStream,
)
from backend.application.ports.events import (
    NotificationFactory,
    RealtimePublisher,
    UserNotifier,
)
from backend.application.ports.home import HomeDeviceDirectory
from backend.application.ports.language import CommandUnderstandingPort, Intent
from backend.application.ports.queries.accounts import AccountQueries
from backend.application.ports.queries.automation import AutomationQueries
from backend.application.ports.queries.boards import BoardQueries
from backend.application.ports.queries.devices import DeviceQueries
from backend.application.ports.queries.scenarios import ScenarioQueries
from backend.application.ports.services import (
    Clock,
    HomeStateStore,
    PasswordHasher,
    SessionTokenIssuer,
)
from backend.application.ports.unit_of_work.accounts import AccountUnitOfWorkFactory
from backend.application.ports.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.ports.voice import (
    ReplyComposer,
    SpeechRecognizer,
    SpeechSynthesizer,
    SpokenCommandUnderstanding,
    VoiceSession,
)
from backend.application.services.automation_service import AutomationService
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.services.command_dispatcher import CommandDispatcher, CommandHandler
from backend.application.services.device_control import DeviceControlService
from backend.application.services.home_provisioning import HomeProvisioning
from backend.application.services.home_state_service import HomeStateService
from backend.application.services.manual_override_reaction import ManualOverrideReaction
from backend.application.services.reaction_dispatcher import ReactionDispatcher
from backend.application.services.scenario_service import ScenarioService
from backend.application.services.voice_service import VoiceCommandService
from backend.application.use_cases.accounts.authenticate_account import AuthenticateAccountUseCase
from backend.application.use_cases.accounts.register_account import RegisterAccountUseCase
from backend.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from backend.application.use_cases.devices.create_device import CreateDeviceUseCase
from backend.application.use_cases.devices.delete_device import DeleteDeviceUseCase
from backend.application.use_cases.devices.switch_device import (
    SwitchAllDevicesUseCase,
    SwitchDeviceUseCase,
)
from backend.application.use_cases.devices.update_device import UpdateDeviceUseCase
from backend.config.settings import Settings
from backend.domain.boards.esp_claim import EspClaim
from backend.domain.climate.climate_demand import DemandCalculator
from backend.domain.devices.capability import Capability
from backend.domain.services.device_selector import DeviceSelector
from backend.infrastructure.clock import SystemClock
from backend.infrastructure.database.engine import build_engine, build_session_factory
from backend.infrastructure.database.queries import (
    SqlAccountQueries,
    SqlAutomationQueries,
    SqlBoardQueries,
    SqlDeviceQueries,
    SqlScenarioQueries,
)
from backend.infrastructure.database.unit_of_work import (
    make_account_unit_of_work,
    make_board_onboarding_unit_of_work,
    make_home_unit_of_work,
)
from backend.infrastructure.esp.adapters import BoardGatewayAdapter, EspMicrophoneAdapter
from backend.infrastructure.esp.connection import (
    EspConnection,
    MicrophoneStreamForwarder,
    MicrophoneStreamResolver,
)
from backend.infrastructure.esp.onboarding import AnnounceBoard, BoardOnboardingGateway
from backend.infrastructure.home_directory import SqlHomeDeviceDirectory
from backend.infrastructure.nlp.embeddings import Embedder
from backend.infrastructure.nlp.factory import build_embedder, build_understanding
from backend.infrastructure.nlp.remote import RemoteUnderstandingClient
from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.redis.event_broker import RedisEventBroker, RedisSubscriber
from backend.infrastructure.redis.state_store import RedisHomeStateStore
from backend.infrastructure.security.password_hasher import Pbkdf2PasswordHasher
from backend.infrastructure.security.session_tokens import JwtSessionTokenIssuer
from backend.infrastructure.telegram.client import TelegramBotClient
from backend.infrastructure.telegram.linking import TelegramLinkTokenIssuer
from backend.infrastructure.telegram.notifier import TelegramNotifier
from backend.infrastructure.voice.recognizer import (
    HttpSpeechRecognizer,
    UnavailableSpeechRecognizer,
)
from backend.infrastructure.voice.session import BufferedVoiceSession
from backend.infrastructure.voice.synthesizer import HttpSpeechSynthesizer
from backend.infrastructure.voice.understanding import SpokenUnderstandingAdapter

APP = Scope.APP
REQUEST = Scope.REQUEST

MAX_HTTP_CONNECTIONS = 20
MAX_HTTP_KEEPALIVE = 5


@dataclass(frozen=True, slots=True)
class CommandHandlerRegistry:
    """Every handler of the command bus, keyed by the intent it serves.

    Args:
        on_device: Handler of "turn this on".
        off_device: Handler of "turn this off".
        on_everything: Handler of "turn everything on".
        off_everything: Handler of "turn everything off".
        temperature_target: Handler of "make it twenty degrees".
        humidity_target: Handler of "make it sixty percent".
        capability: Handler of "make it colder" and "switch the conditioner on".
        describe: Handler of "what is the state of the house".
        read_temperature: Handler of "how warm is it".
        read_humidity: Handler of "how wet is it".
        schedule: Handler of "make it twenty degrees in half an hour".
        cancel: Handler of "cancel the scenario".

    Returns:
        None.
    """

    on_device: SwitchDeviceHandler
    off_device: SwitchDeviceHandler
    on_everything: SwitchAllHandler
    off_everything: SwitchAllHandler
    temperature_target: SetClimateTargetHandler
    humidity_target: SetClimateTargetHandler
    capability: RunCapabilityHandler
    describe: DescribeHomeHandler
    read_temperature: ReadTemperatureHandler
    read_humidity: ReadHumidityHandler
    schedule: ScheduleScenarioHandler
    cancel: CancelScenarioHandler

    def by_intent(self) -> dict[Intent, CommandHandler]:
        """Return the handlers indexed by the intent each one serves.

        Returns:
            dict[Intent, CommandHandler]: Handlers of the command bus.
        """
        return {
            Intent.SWITCH_DEVICE: self.on_device,
            Intent.SWITCH_ALL: self.on_everything,
            Intent.SET_TEMPERATURE: self.temperature_target,
            Intent.SET_HUMIDITY: self.humidity_target,
            Intent.RUN_CAPABILITY: self.capability,
            Intent.DESCRIBE_HOME: self.describe,
            Intent.READ_TEMPERATURE: self.read_temperature,
            Intent.READ_HUMIDITY: self.read_humidity,
            Intent.SCHEDULE_SCENARIO: self.schedule,
            Intent.CANCEL_SCENARIO: self.cancel,
        }


class CoreProvider(Provider):
    """Configuration, clock, cryptography and the long lived clients."""

    scope = APP

    @provide(scope=APP)
    def provide_clock(self) -> Clock:
        """Build the clock every timestamp arrives from.

        Returns:
            Clock: Clock reading the system time.
        """
        return SystemClock()

    @provide(scope=APP)
    def provide_password_hasher(self) -> PasswordHasher:
        """Build the hasher stored passwords are produced by.

        Returns:
            PasswordHasher: PBKDF2 hasher.
        """
        return Pbkdf2PasswordHasher()

    @provide(scope=APP)
    def provide_session_tokens(self, settings: Settings) -> SessionTokenIssuer:
        """Build the issuer of the session tokens.

        Args:
            settings: Configuration of the deployment.

        Returns:
            SessionTokenIssuer: Issuer signing with HS256.
        """
        return JwtSessionTokenIssuer(
            secret=settings.auth.token_secret,
            lifetime_minutes=settings.auth.session_lifetime_minutes,
        )

    @provide(scope=APP)
    async def provide_engine(self, settings: Settings) -> AsyncIterator[AsyncEngine]:
        """Build the engine the whole process shares.

        Args:
            settings: Configuration of the deployment.

        Yields:
            AsyncEngine: Engine bound to the configured database.
        """
        engine = build_engine(
            str(settings.database.url),
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            pool_max_overflow=settings.database.pool_max_overflow,
            pool_recycle_sec=settings.database.pool_recycle_sec,
        )
        yield engine
        await engine.dispose()

    @provide(scope=APP)
    def provide_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        """Build the factory the units of work ask for their sessions.

        Args:
            engine: Engine to bind sessions to.

        Returns:
            async_sessionmaker[AsyncSession]: Session factory.
        """
        return build_session_factory(engine)

    @provide(scope=APP)
    async def provide_redis(self, settings: Settings) -> AsyncIterator[Redis]:
        """Build the connection every volatile key of the system is stored in.

        Args:
            settings: Configuration of the deployment.

        Yields:
            Redis: Connection to the configured server.
        """
        client: Redis = Redis.from_url(settings.redis.url, password=settings.redis.password)
        yield client
        await client.aclose()

    @provide(scope=APP)
    async def provide_http_client(self, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
        """Build the connection pool talking to the speech and model services.

        Args:
            settings: Configuration of the deployment.

        Yields:
            httpx.AsyncClient: Connection pool.
        """
        client = httpx.AsyncClient(
            timeout=settings.voice.timeout_sec,
            limits=httpx.Limits(
                max_connections=MAX_HTTP_CONNECTIONS,
                max_keepalive_connections=MAX_HTTP_KEEPALIVE,
            ),
        )
        yield client
        await client.aclose()


class PersistenceProvider(Provider):
    """Read side, transaction boundaries and the cheap device reads."""

    scope = APP

    @provide(scope=APP)
    def provide_account_queries(self, engine: AsyncEngine) -> AccountQueries:
        """Build the reads of the accounts.

        Args:
            engine: Engine to read from.

        Returns:
            AccountQueries: Reads of the accounts.
        """
        return SqlAccountQueries(engine)

    @provide(scope=APP)
    def provide_device_queries(self, engine: AsyncEngine) -> DeviceQueries:
        """Build the reads of the device configuration.

        Args:
            engine: Engine to read from.

        Returns:
            DeviceQueries: Reads of the devices.
        """
        return SqlDeviceQueries(engine)

    @provide(scope=APP)
    def provide_automation_queries(self, engine: AsyncEngine) -> AutomationQueries:
        """Build the reads of the automation configuration.

        Args:
            engine: Engine to read from.

        Returns:
            AutomationQueries: Reads of the automation configuration.
        """
        return SqlAutomationQueries(engine)

    @provide(scope=APP)
    def provide_scenario_queries(self, engine: AsyncEngine) -> ScenarioQueries:
        """Build the reads of the scenarios.

        Args:
            engine: Engine to read from.

        Returns:
            ScenarioQueries: Reads of the scenarios.
        """
        return SqlScenarioQueries(engine)

    @provide(scope=APP)
    def provide_board_queries(self, engine: AsyncEngine) -> BoardQueries:
        """Build the reads of the boards.

        Args:
            engine: Engine to read from.

        Returns:
            BoardQueries: Reads of the boards.
        """
        return SqlBoardQueries(engine)

    @provide(scope=APP)
    def provide_account_uow(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AccountUnitOfWorkFactory:
        """Build the factory of the account transactions.

        Args:
            session_factory: Factory producing sessions.

        Returns:
            AccountUnitOfWorkFactory: Factory over the accounts.
        """
        return make_account_unit_of_work(session_factory)

    @provide(scope=APP)
    def provide_home_uow(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> HomeUnitOfWorkFactory:
        """Build the factory of the home transactions.

        Args:
            session_factory: Factory producing sessions.

        Returns:
            HomeUnitOfWorkFactory: Factory over the configuration of a home.
        """
        return make_home_unit_of_work(session_factory)

    @provide(scope=APP)
    def provide_onboarding_uow(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> BoardOnboardingUnitOfWorkFactory:
        """Build the factory of the board transactions.

        Args:
            session_factory: Factory producing sessions.

        Returns:
            BoardOnboardingUnitOfWorkFactory: Factory over the boards.
        """
        return make_board_onboarding_unit_of_work(session_factory)

    @provide(scope=APP)
    def provide_home_directory(self, engine: AsyncEngine) -> HomeDeviceDirectory:
        """Build the cheap reads the board reports are translated with.

        Args:
            engine: Engine to read from.

        Returns:
            HomeDeviceDirectory: Reads of the devices of a home.
        """
        return SqlHomeDeviceDirectory(engine)


class VolatileStateProvider(Provider):
    """The state store, the realtime stream and the messenger chats."""

    scope = APP

    @provide(scope=APP)
    def provide_state_store(self, redis: Redis, settings: Settings) -> HomeStateStore:
        """Build the durable home of the volatile state.

        Args:
            redis: Connection the state is stored in.
            settings: Configuration of the deployment.

        Returns:
            HomeStateStore: Redis backed state store.
        """
        return RedisHomeStateStore(redis, settings.redis.key_prefix)

    @provide(scope=APP)
    def provide_realtime(self, redis: Redis, settings: Settings) -> RealtimePublisher:
        """Build the publisher of the realtime events.

        Args:
            redis: Connection the events are written to.
            settings: Configuration of the deployment.

        Returns:
            RealtimePublisher: Redis Pub/Sub publisher.
        """
        return RedisEventBroker(redis, settings.redis.key_prefix)

    @provide(scope=APP)
    def provide_subscriber(self, settings: Settings) -> RedisSubscriber:
        """Build the reader the websocket hub consumes.

        The subscriber owns a blocking connection of its own, because
        ``pubsub.listen`` blocks and blocking the event loop of a request would be
        worse than a second connection.

        Args:
            settings: Configuration of the deployment.

        Returns:
            RedisSubscriber: Blocking subscriber as an async iterable.
        """
        return RedisSubscriber(
            url=settings.redis.url,
            password=settings.redis.password,
            key_prefix=settings.redis.key_prefix,
        )

    @provide(scope=APP)
    def provide_chat_sessions(self, redis: Redis, settings: Settings) -> RedisChatSessionStore:
        """Build the mapping of messenger chats onto accounts.

        Args:
            redis: Connection the mapping is stored in.
            settings: Configuration of the deployment.

        Returns:
            RedisChatSessionStore: Chat to account mapping.
        """
        return RedisChatSessionStore(redis, settings.redis.key_prefix)


class TelegramProvider(Provider):
    """The single bot instance and what it is used for."""

    scope = APP

    @provide(scope=APP)
    def provide_bot(self, settings: Settings) -> TelegramBotClient:
        """Build the one bot instance of the process.

        Args:
            settings: Configuration of the deployment.

        Returns:
            TelegramBotClient: Bot shared by polling and notifications.
        """
        return TelegramBotClient(settings.telegram.bot_token)

    @provide(scope=APP)
    def provide_link_tokens(self, tokens: SessionTokenIssuer) -> TelegramLinkTokenIssuer:
        """Build the issuer of the one time link tokens.

        Args:
            tokens: Issuer whose secret and configuration are reused.

        Returns:
            TelegramLinkTokenIssuer: Issuer of the link tokens.
        """
        return TelegramLinkTokenIssuer(tokens)

    @provide(scope=APP)
    def provide_notifier(
        self,
        bot: TelegramBotClient,
        sessions: RedisChatSessionStore,
        settings: Settings,
    ) -> UserNotifier:
        """Build the delivery channel of the notifications.

        Args:
            bot: The one bot instance of the process.
            sessions: Chats linked to accounts.
            settings: Configuration of the deployment.

        Returns:
            UserNotifier: Telegram delivery channel.
        """
        return TelegramNotifier(
            client=bot,
            sessions=sessions,
            operator_chat_id=settings.telegram.notify_chat_id,
        )


class LanguageProvider(Provider):
    """The understanding pipeline and the encoder it is built on."""

    scope = APP

    @provide(scope=APP)
    def provide_embedder(self, settings: Settings) -> Embedder:
        """Load the sentence encoder named by the configuration.

        Args:
            settings: Configuration of the deployment.

        Returns:
            Embedder: Loaded encoder.
        """
        return build_embedder(settings)

    @provide(scope=APP)
    def provide_understanding(
        self,
        engine: AsyncEngine,
        embedder: Embedder,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> CommandUnderstandingPort:
        """Build the pipeline the deployment asked for.

        Args:
            engine: Engine the reference phrases are read from.
            embedder: Encoder turning a phrase into a vector.
            client: Connection to the remote model host.
            settings: Configuration of the deployment.

        Returns:
            CommandUnderstandingPort: Local or remote first pipeline.
        """
        return build_understanding(engine, embedder, client, settings)

    @provide(scope=APP)
    def provide_remote_understanding(
        self, client: httpx.AsyncClient, settings: Settings
    ) -> SpokenCommandUnderstanding:
        """Build the remote understanding of a transcribed sentence.

        Args:
            client: Connection to the remote model host.
            settings: Configuration of the deployment.

        Returns:
            SpokenCommandUnderstanding: Adapter over the remote model, or one that
            always has no answer when no model is configured.
        """
        remote = None
        if settings.voice.neural_commands and settings.voice.bootstrap_url:
            remote = RemoteUnderstandingClient(
                client=client,
                base_url=settings.voice.bootstrap_url,
                timeout_sec=settings.voice.timeout_sec,
            )
        return SpokenUnderstandingAdapter(remote)


class VoiceProvider(Provider):
    """The three speech clients and the buffering of a microphone stream."""

    scope = APP

    @provide(scope=APP)
    def provide_recognizer(self, client: httpx.AsyncClient, settings: Settings) -> SpeechRecognizer:
        """Build the recognizer.

        Args:
            client: Connection to the speech service.
            settings: Configuration of the deployment.

        Returns:
            SpeechRecognizer: HTTP recognizer, or a stub while voice is off.
        """
        if not settings.voice.active:
            return UnavailableSpeechRecognizer()
        return HttpSpeechRecognizer(
            client=client,
            base_url=settings.voice.base_url,
            timeout_sec=settings.voice.timeout_sec,
        )

    @provide(scope=APP)
    def provide_synthesizer(
        self, client: httpx.AsyncClient, settings: Settings
    ) -> SpeechSynthesizer:
        """Build the synthesizer.

        Args:
            client: Connection to the speech service.
            settings: Configuration of the deployment.

        Returns:
            SpeechSynthesizer: HTTP synthesizer.
        """
        return HttpSpeechSynthesizer(
            client=client,
            base_url=settings.voice.base_url,
            timeout_sec=settings.voice.timeout_sec,
            enabled=settings.voice.active and settings.voice.synthesis_enabled,
        )

    @provide(scope=APP)
    def provide_voice_session(
        self, recognizer: SpeechRecognizer, settings: Settings
    ) -> VoiceSession:
        """Build the buffering of a microphone stream.

        Args:
            recognizer: Speech recognition applied to a finished clip.
            settings: Configuration of the deployment.

        Returns:
            VoiceSession: Buffering of one phrase.
        """
        return BufferedVoiceSession(
            recognizer=recognizer,
            sample_rate=settings.voice.sample_rate,
            max_audio_sec=settings.voice.max_audio_sec,
        )


class DomainProvider(Provider):
    """The domain services the application delegates its decisions to."""

    scope = APP

    @provide(scope=APP)
    def provide_device_selector(self) -> DeviceSelector:
        """Build the resolver of the device a command is meant for.

        Returns:
            DeviceSelector: Resolver of devices.
        """
        return DeviceSelector()

    @provide(scope=APP)
    def provide_demand_calculator(self) -> DemandCalculator:
        """Build the model component deciding what the climate asks for.

        Returns:
            DemandCalculator: Model component of the climate band.
        """
        return DemandCalculator()


class BoardProvider(Provider):
    """The WebSocket transport, its two facades and the two seams of its graph."""

    scope = APP

    report = alias(source=HomeStateService, provides=BoardReport)

    @provide(scope=APP)
    def provide_microphone_resolver(self, container: AsyncContainer) -> MicrophoneStreamResolver:
        """Build the forwardable callable the audio sink is made of.

        The audio of a board reaches the voice pipeline, and the voice pipeline
        needs the microphone port of the very connection that owns this sink, so
        the two cannot be handed to each other while the graph is built. The
        callable closes over the container and resolves the stream the first time
        audio arrives, which is why it is a callable and not an object.

        Args:
            container: Container the stream is resolved from.

        Returns:
            MicrophoneStreamResolver: Callable returning the microphone stream.
        """
        return microphone_resolver(container)

    @provide(scope=APP)
    def provide_microphone_forwarder(
        self, resolve: MicrophoneStreamResolver
    ) -> MicrophoneStreamForwarder:
        """Build the sink the board audio is handed to.

        Args:
            resolve: Callable returning the microphone stream.

        Returns:
            MicrophoneStreamForwarder: Sink forwarding to the voice pipeline.
        """
        return MicrophoneStreamForwarder(resolve)

    @provide(scope=APP)
    def provide_announce_board(self, container: AsyncContainer) -> AnnounceBoard:
        """Build the forwardable callable that publishes an unpaired board.

        The onboarding service needs a gateway over the connection that asks it
        to announce, so the service is resolved from the container on the first
        handshake instead of being injected while the graph is built.

        Args:
            container: Container the onboarding service is resolved from.

        Returns:
            AnnounceBoard: Callable publishing or refreshing an offer.
        """
        return announce_board(container)

    @provide(scope=APP)
    def provide_onboarding_gateway(
        self,
        uow: BoardOnboardingUnitOfWorkFactory,
        announce: AnnounceBoard,
        clock: Clock,
    ) -> BoardOnboardingGateway:
        """Build the operations a handshake raises.

        Args:
            uow: Factory producing transactions over the boards.
            announce: Publishes or refreshes the offer of an unpaired board.
            clock: Source of the current time.

        Returns:
            BoardOnboardingGateway: Application side of the handshake.
        """
        return BoardOnboardingGateway(uow, announce, clock)

    @provide(scope=APP)
    def provide_connection(
        self,
        report: BoardReport,
        microphone: MicrophoneStreamForwarder,
        onboarding: BoardOnboardingGateway,
        settings: Settings,
    ) -> EspConnection:
        """Build the WebSocket server the boards dial in to.

        The socket port is the API port plus one, which keeps the two listeners of
        a single host apart without asking for another setting.

        Args:
            report: Sink the inbound reports are handed to.
            microphone: Sink the audio is handed to.
            onboarding: Gateway answering the questions a handshake raises.
            settings: Configuration of the deployment.

        Returns:
            EspConnection: Board transport.
        """
        return EspConnection(
            report=report,
            microphone=microphone,
            onboarding=onboarding,
            host=settings.server.host,
            port=settings.server.port + 1,
            command_timeout_sec=settings.board.command_timeout_sec,
        )

    @provide(scope=APP)
    def provide_board_gateway(self, connection: EspConnection) -> BoardGateway:
        """Build the relay facade the application drives the hardware with.

        Args:
            connection: Transport level board connection.

        Returns:
            BoardGateway: Relay facade.
        """
        return BoardGatewayAdapter(connection)

    @provide(scope=APP)
    def provide_microphone(self, connection: EspConnection) -> MicrophonePort:
        """Build the microphone facade of a board.

        Args:
            connection: Transport level board connection.

        Returns:
            MicrophonePort: Microphone facade.
        """
        return EspMicrophoneAdapter(connection)


class ApplicationProvider(Provider):
    """Reactions, application services, the command bus and the voice pipeline."""

    scope = APP

    @provide(scope=APP)
    def provide_reactions(
        self,
        home_uow: HomeUnitOfWorkFactory,
        state_store: HomeStateStore,
        clock: Clock,
        settings: Settings,
    ) -> ReactionDispatcher:
        """Build the dispatcher of the facts the aggregates record.

        Args:
            home_uow: Factory producing transactions over the configuration.
            state_store: Durable home of the volatile state.
            clock: Source of the current time.
            settings: Configuration of the deployment.

        Returns:
            ReactionDispatcher: Dispatcher handing facts to every subscriber.
        """
        return ReactionDispatcher(
            (
                HomeProvisioning(home_uow),
                ManualOverrideReaction(
                    state_store=state_store,
                    clock=clock,
                    override_minutes=settings.automation.manual_override_minutes,
                ),
            )
        )

    @provide(scope=APP)
    def provide_device_control(
        self,
        home_uow: HomeUnitOfWorkFactory,
        boards: BoardGateway,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        reactions: ReactionDispatcher,
        clock: Clock,
        selector: DeviceSelector,
    ) -> DeviceControlService:
        """Build the one path every hardware change goes through.

        Args:
            home_uow: Factory producing transactions over the configuration.
            boards: Gateway to the physical hardware.
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.
            reactions: Hands recorded facts to their subscribers.
            clock: Source of the current time.
            selector: Resolves devices by capability.

        Returns:
            DeviceControlService: Service performing capabilities.
        """
        return DeviceControlService(
            home_uow=home_uow,
            boards=boards,
            state_store=state_store,
            realtime=realtime,
            dispatcher=reactions,
            clock=clock,
            selector=selector,
        )

    @provide(scope=APP)
    def provide_home_state_service(
        self,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        devices_of_home: HomeDeviceDirectory,
    ) -> HomeStateService:
        """Build the sink every inbound board report is handed to.

        Args:
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.
            notifier: Delivery channel for notifications.
            notifications: Builds the wording of every message.
            clock: Source of the current time.
            devices_of_home: Cheap reads of the configuration.

        Returns:
            HomeStateService: Consumer of everything the boards report.
        """
        return HomeStateService(
            state_store=state_store,
            realtime=realtime,
            notifier=notifier,
            notifications=notifications,
            clock=clock,
            devices_of_home=devices_of_home,
        )

    @provide(scope=APP)
    def provide_automation(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
        clock: Clock,
    ) -> AutomationService:
        """Build one automation cycle of a home.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            state_store: Durable home of the volatile state.
            demands: Model component deciding what the climate is asking for.
            clock: Source of the current time.

        Returns:
            AutomationService: One automation cycle.
        """
        return AutomationService(home_uow, control, state_store, demands, clock)

    @provide(scope=APP)
    def provide_scenarios(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        reactions: ReactionDispatcher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        settings: Settings,
    ) -> ScenarioService:
        """Build the lifecycle of the scenarios of a home.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.
            reactions: Hands recorded facts to their subscribers.
            notifier: Delivery channel for notifications.
            notifications: Builds the wording of every message.
            clock: Source of the current time.
            settings: Configuration of the deployment.

        Returns:
            ScenarioService: Lifecycle of the scenarios.
        """
        return ScenarioService(
            home_uow=home_uow,
            control=control,
            state_store=state_store,
            realtime=realtime,
            dispatcher=reactions,
            notifier=notifier,
            notifications=notifications,
            clock=clock,
            summary_window_sec=settings.automation.scenario_summary_ttl_sec,
        )

    @provide(scope=APP)
    def provide_board_onboarding(
        self,
        uow: BoardOnboardingUnitOfWorkFactory,
        queries: BoardQueries,
        boards: BoardGateway,
        realtime: RealtimePublisher,
        clock: Clock,
        settings: Settings,
    ) -> BoardOnboardingService:
        """Build the lifecycle of the boards of the system.

        Args:
            uow: Factory producing transactions over the boards.
            queries: Cheap reads used to answer what the interface asks for.
            boards: Gateway telling whether a board is connected.
            realtime: Publisher of events to the open clients.
            clock: Source of the current time.
            settings: Configuration of the deployment.

        Returns:
            BoardOnboardingService: Lifecycle of the boards.
        """
        return BoardOnboardingService(
            onboarding_uow=uow,
            queries=queries,
            boards=boards,
            realtime=realtime,
            clock=clock,
            claim_ttl_sec=settings.board.claim_ttl_sec,
        )

    @provide(scope=APP)
    def provide_handlers(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        selector: DeviceSelector,
        demands: DemandCalculator,
        state_store: HomeStateStore,
        device_queries: DeviceQueries,
        scenario_queries: ScenarioQueries,
        automation_queries: AutomationQueries,
        scenarios: ScenarioService,
        clock: Clock,
    ) -> CommandHandlerRegistry:
        """Build the handler of every intent a person may say.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            selector: Resolves the device a reference points at.
            demands: Model component deciding which capability a target implies.
            state_store: Durable home of the volatile state.
            device_queries: Reads of the device configuration.
            scenario_queries: Reads of the scenarios.
            automation_queries: Reads of the automation configuration.
            scenarios: Service owning the lifecycle of the scenarios.
            clock: Source of the current time.

        Returns:
            CommandHandlerRegistry: Handlers of the command bus.
        """
        return CommandHandlerRegistry(
            on_device=SwitchDeviceHandler(
                home_uow, control, selector, Capability.ON, Capability.OFF, True
            ),
            off_device=SwitchDeviceHandler(
                home_uow, control, selector, Capability.ON, Capability.OFF, False
            ),
            on_everything=SwitchAllHandler(home_uow, control, Capability.ON, True),
            off_everything=SwitchAllHandler(home_uow, control, Capability.OFF, False),
            temperature_target=SetClimateTargetHandler(home_uow, demands, True),
            humidity_target=SetClimateTargetHandler(home_uow, demands, False),
            capability=RunCapabilityHandler(home_uow, control, state_store, demands),
            describe=DescribeHomeHandler(
                state_store, device_queries, scenario_queries, automation_queries, clock
            ),
            read_temperature=ReadTemperatureHandler(state_store),
            read_humidity=ReadHumidityHandler(state_store),
            schedule=ScheduleScenarioHandler(scenarios, demands),
            cancel=CancelScenarioHandler(scenarios, scenario_queries),
        )

    @provide(scope=APP)
    def provide_dispatcher(
        self,
        understanding: CommandUnderstandingPort,
        handlers: CommandHandlerRegistry,
        composer: ReplyComposer,
    ) -> CommandDispatcher:
        """Build the command bus.

        Args:
            understanding: Pipeline turning a sentence into a structured command.
            handlers: Handler of every intent that can be carried out.
            composer: Builds the wording of the answers.

        Returns:
            CommandDispatcher: Command bus.
        """
        return CommandDispatcher(understanding, handlers.by_intent(), composer)

    @provide(scope=APP)
    def provide_voice(
        self,
        dispatcher: CommandDispatcher,
        sessions: VoiceSession,
        recognizer: SpeechRecognizer,
        synthesizer: SpeechSynthesizer,
        microphone: MicrophonePort,
        composer: ReplyComposer,
        settings: Settings,
    ) -> MicrophoneStream:
        """Build the voice pipeline of the boards.

        Args:
            dispatcher: Command bus carrying out what was said.
            sessions: Collects the microphone stream into phrases.
            recognizer: Speech recognition.
            synthesizer: Speech synthesis.
            microphone: Opens the microphone of a board and plays answers on it.
            composer: Builds the wording of the answers.
            settings: Configuration of the deployment.

        Returns:
            MicrophoneStream: Voice pipeline of the boards.
        """
        return VoiceCommandService(
            dispatcher=dispatcher,
            sessions=sessions,
            recognizer=recognizer,
            synthesizer=synthesizer,
            microphone=microphone,
            composer=composer,
            sample_rate=settings.voice.sample_rate,
            max_audio_sec=settings.voice.max_audio_sec,
        )


class UseCaseProvider(Provider):
    """The entry points a request calls. One set per request."""

    scope = REQUEST

    @provide(scope=REQUEST)
    def provide_register_account(
        self,
        uow: AccountUnitOfWorkFactory,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
        reactions: ReactionDispatcher,
        clock: Clock,
    ) -> RegisterAccountUseCase:
        """Build the account creation.

        Args:
            uow: Factory producing transactions over the accounts.
            hasher: Turns a plain password into a stored form.
            tokens: Issues the session token.
            reactions: Announces the fact that the account exists.
            clock: Source of the current time.

        Returns:
            RegisterAccountUseCase: Account creation.
        """
        return RegisterAccountUseCase(uow, hasher, tokens, reactions, clock)

    @provide(scope=REQUEST)
    def provide_authenticate_account(
        self,
        queries: AccountQueries,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
    ) -> AuthenticateAccountUseCase:
        """Build the login.

        Args:
            queries: Cheap reads of the accounts.
            hasher: Compares a plain password with a stored one.
            tokens: Issues the session token.

        Returns:
            AuthenticateAccountUseCase: Login.
        """
        return AuthenticateAccountUseCase(queries, hasher, tokens)

    @provide(scope=REQUEST)
    def provide_create_device(
        self,
        uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        reactions: ReactionDispatcher,
    ) -> CreateDeviceUseCase:
        """Build the device creation.

        Args:
            uow: Factory producing transactions over the configuration.
            realtime: Publisher of events to the open clients.
            reactions: Announces the fact that the configuration changed.

        Returns:
            CreateDeviceUseCase: Device creation.
        """
        return CreateDeviceUseCase(uow, realtime, reactions)

    @provide(scope=REQUEST)
    def provide_update_device(
        self,
        uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        reactions: ReactionDispatcher,
    ) -> UpdateDeviceUseCase:
        """Build the device change.

        Args:
            uow: Factory producing transactions over the configuration.
            realtime: Publisher of events to the open clients.
            reactions: Announces the fact that the configuration changed.

        Returns:
            UpdateDeviceUseCase: Device change.
        """
        return UpdateDeviceUseCase(uow, realtime, reactions)

    @provide(scope=REQUEST)
    def provide_delete_device(
        self,
        uow: HomeUnitOfWorkFactory,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
    ) -> DeleteDeviceUseCase:
        """Build the device removal.

        Args:
            uow: Factory producing transactions over the configuration.
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.

        Returns:
            DeleteDeviceUseCase: Device removal.
        """
        return DeleteDeviceUseCase(uow, state_store, realtime)

    @provide(scope=REQUEST)
    def provide_switch_device(
        self, uow: HomeUnitOfWorkFactory, control: DeviceControlService
    ) -> SwitchDeviceUseCase:
        """Build the switch of one device.

        Args:
            uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.

        Returns:
            SwitchDeviceUseCase: Switch of one device.
        """
        return SwitchDeviceUseCase(uow, control)

    @provide(scope=REQUEST)
    def provide_switch_all_devices(
        self, uow: HomeUnitOfWorkFactory, control: DeviceControlService
    ) -> SwitchAllDevicesUseCase:
        """Build the switch of every device of a home.

        Args:
            uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.

        Returns:
            SwitchAllDevicesUseCase: Switch of every device.
        """
        return SwitchAllDevicesUseCase(uow, control)

    @provide(scope=REQUEST)
    def provide_configure_board_network(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        boards: BoardGateway,
        clock: Clock,
    ) -> ConfigureBoardNetworkUseCase:
        """Build the change of the network of a board.

        Args:
            onboarding_uow: Factory producing transactions over the boards.
            boards: Gateway telling the boards what to do.
            clock: Source of the current time.

        Returns:
            ConfigureBoardNetworkUseCase: Change of the network of a board.
        """
        return ConfigureBoardNetworkUseCase(onboarding_uow, boards, clock)


def microphone_resolver(container: AsyncContainer) -> MicrophoneStreamResolver:
    """Return the callable the board audio sink forwards to.

    Args:
        container: Container the stream is resolved from.

    Returns:
        MicrophoneStreamResolver: Callable returning the microphone stream.
    """

    async def resolve() -> MicrophoneStream:
        """Return the stream the microphone audio is handed to.

        Returns:
            MicrophoneStream: Stream of the voice pipeline.
        """
        return await container.get(MicrophoneStream)

    return resolve


def announce_board(container: AsyncContainer) -> AnnounceBoard:
    """Return the callable publishing the offer of an unpaired board.

    Args:
        container: Container the onboarding service is resolved from.

    Returns:
        AnnounceBoard: Callable publishing or refreshing an offer.
    """

    async def announce(command: AnnounceBoardCommand) -> EspClaim:
        """Publish or refresh the offer of the board that presented the key.

        Args:
            command: Key and label the board presented.

        Returns:
            EspClaim: Open offer of that board.
        """
        service = await container.get(BoardOnboardingService)
        return await service.announce(command)

    return announce
