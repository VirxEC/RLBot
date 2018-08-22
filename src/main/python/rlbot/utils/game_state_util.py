import flatbuffers
from rlbot.messages.flat import Float, RotatorPartial, Vector3Partial, DesiredPhysics, DesiredGameState, \
    DesiredCarState, DesiredBallState, Bool

from rlbot.utils.structures import game_data_struct
from rlbot.messages.flat import GameTickPacket


class Rotator:

    def __init__(self, pitch=None, yaw=None, roll=None):
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll

    def convert_to_flat(self, builder):
        if self.pitch is None and self.yaw is None and self.roll is None:
            return None  # If no value has to be set this saves some bytes in the builder, will get handled correctly

        RotatorPartial.RotatorPartialStart(builder)
        if self.pitch is not None:
            RotatorPartial.RotatorPartialAddPitch(builder, Float.CreateFloat(builder, self.pitch))
        if self.yaw is not None:
            RotatorPartial.RotatorPartialAddYaw(builder, Float.CreateFloat(builder, self.yaw))
        if self.roll is not None:
            RotatorPartial.RotatorPartialAddRoll(builder, Float.CreateFloat(builder, self.roll))
        return RotatorPartial.RotatorPartialEnd(builder)


class Vector3:

    def __init__(self, x=None, y=None, z=None):
        self.x = x
        self.y = y
        self.z = z

    def convert_to_flat(self, builder):
        if self.x is None and self.y is None and self.z is None:
            return None  # If no value has to be set this saves some bytes in the builder, will get handled correctly

        Vector3Partial.Vector3PartialStart(builder)
        if self.x is not None:
            Vector3Partial.Vector3PartialAddX(builder, Float.CreateFloat(builder, self.x))
        if self.y is not None:
            Vector3Partial.Vector3PartialAddY(builder, Float.CreateFloat(builder, self.y))
        if self.z is not None:
            Vector3Partial.Vector3PartialAddZ(builder, Float.CreateFloat(builder, self.z))
        return Vector3Partial.Vector3PartialEnd(builder)


class Physics:

    def __init__(self, location: Vector3 = None, rotation: Rotator = None, velocity: Vector3 = None,
                 angular_velocity: Vector3 = None):
        self.location = location
        self.rotation = rotation
        self.velocity = velocity
        self.angular_velocity = angular_velocity

    def convert_to_flat(self, builder):
        location_offset = None if self.location is None else self.location.convert_to_flat(builder)
        rotation_offset = None if self.rotation is None else self.rotation.convert_to_flat(builder)
        velocity_offset = None if self.velocity is None else self.velocity.convert_to_flat(builder)
        angular_velocity_offset = None if self.angular_velocity is None else self.angular_velocity.convert_to_flat(
            builder)

        if location_offset is None and rotation_offset is None and velocity_offset is None and \
                angular_velocity_offset is None:
            return None  # If no value has to be set this saves some bytes in the builder, will get handled correctly

        DesiredPhysics.DesiredPhysicsStart(builder)
        if location_offset is not None:
            DesiredPhysics.DesiredPhysicsAddLocation(builder, location_offset)
        if rotation_offset is not None:
            DesiredPhysics.DesiredPhysicsAddRotation(builder, rotation_offset)
        if velocity_offset is not None:
            DesiredPhysics.DesiredPhysicsAddVelocity(builder, velocity_offset)
        if angular_velocity_offset is not None:
            DesiredPhysics.DesiredPhysicsAddAngularVelocity(builder, angular_velocity_offset)
        return DesiredPhysics.DesiredPhysicsEnd(builder)


class BallState:

    def __init__(self, physics: Physics = None):
        self.physics = physics

    def convert_to_flat(self, builder):
        physics_offset = None if self.physics is None else self.physics.convert_to_flat(builder)

        if physics_offset is not None:
            DesiredBallState.DesiredBallStateStart(builder)
            DesiredBallState.DesiredBallStateAddPhysics(builder, physics_offset)
            return DesiredBallState.DesiredBallStateEnd(builder)
        else:
            return None  # This will get handled correctly and is better than taking space while not having to


class CarState:

    def __init__(self, physics: Physics = None, boost_amount: Float = None, jumped: Bool = None,
                 double_jumped: Bool = None):
        self.physics = physics
        self.boost_amount = boost_amount
        self.jumped = jumped
        self.double_jumped = double_jumped

    def convert_to_flat(self, builder):
        physics_offset = None if self.physics is None else self.physics.convert_to_flat(builder)

        if physics_offset is None and self.boost_amount is None and self.jumped is None and self.double_jumped is None:
            return None  # If no value has to be set this saves some bytes in the builder, will get handled correctly

        DesiredCarState.DesiredCarStateStart(builder)
        if physics_offset is not None:
            DesiredCarState.DesiredCarStateAddPhysics(builder, physics_offset)
        if self.boost_amount is not None:
            DesiredCarState.DesiredCarStateAddBoostAmount(builder, Float.CreateFloat(builder, self.boost_amount))
        if self.jumped is not None:
            DesiredCarState.DesiredCarStateAddJumped(builder, Bool.CreateBool(builder, self.jumped))
        if self.double_jumped is not None:
            DesiredCarState.DesiredCarStateAddDoubleJumped(builder, Bool.CreateBool(builder, self.double_jumped))
        return DesiredCarState.DesiredCarStateEnd(builder)


class GameState:

    def __init__(self, ball: BallState = None, cars=None):
        self.ball = ball
        self.cars = cars

    def convert_to_flat(self, builder=None):
        if self.ball is None and self.cars is None:
            return None

        if builder is None:
            builder = flatbuffers.Builder(0)

        ball_offset = None if self.ball is None else self.ball.convert_to_flat(builder)

        car_offsets = []
        if self.cars is not None:
            max_index = max(self.cars.keys())
            for i in range(0, max_index + 1):
                if i in self.cars:
                    car = self.cars[i]
                else:
                    car = CarState()
                car_offset = car.convert_to_flat(builder)
                car_offsets.append(car_offset)

        car_list_offset = None
        if len(car_offsets) > 0:
            DesiredGameState.DesiredGameStateStartCarStatesVector(builder, len(car_offsets))
            for i in reversed(range(0, len(car_offsets))):
                builder.PrependUOffsetTRelative(car_offsets[i])
            car_list_offset = builder.EndVector(len(car_offsets))

        DesiredGameState.DesiredGameStateStart(builder)
        if ball_offset is not None:
            DesiredGameState.DesiredGameStateAddBallState(builder, ball_offset)
        if car_list_offset is not None:
            DesiredGameState.DesiredGameStateAddCarStates(builder, car_list_offset)

        return DesiredGameState.DesiredGameStateEnd(builder)

    @staticmethod
    def create_from_gametickpacket(game_tick_packet):
        game_state = GameState()
        if isinstance(game_tick_packet, game_data_struct.GameTickPacket):
            car_states = {}
            for i in range(game_tick_packet.num_cars):
                car = game_tick_packet.game_cars[i]
                print(car.physics.location.x)
                car_states[i] = CarState(physics=Physics(location=Vector3(
                    x=car.physics.location.x,
                    y=car.physics.location.y,
                    z=car.physics.location.z
                ), rotation=Rotator(
                    pitch=car.physics.rotation.pitch,
                    yaw=car.physics.rotation.yaw,
                    roll=car.physics.rotation.roll
                ), velocity=Vector3(
                    x=car.physics.velocity.x,
                    y=car.physics.velocity.y,
                    z=car.physics.velocity.z
                ), angular_velocity=Vector3(
                    x=car.physics.angular_velocity.x,
                    y=car.physics.angular_velocity.y,
                    z=car.physics.angular_velocity.z
                )), boost_amount=car.boost, jumped=car.jumped, double_jumped=car.double_jumped)
            game_state.cars = car_states
            ball = game_tick_packet.game_ball
            game_state.ball = BallState(physics=Physics(location=Vector3(
                x=ball.physics.location.x,
                y=ball.physics.location.y,
                z=ball.physics.location.z
            ), rotation=Rotator(
                pitch=ball.physics.rotation.pitch,
                yaw=ball.physics.rotation.yaw,
                roll=ball.physics.rotation.roll
            ), velocity=Vector3(
                x=ball.physics.velocity.x,
                y=ball.physics.velocity.y,
                z=ball.physics.velocity.z
            ), angular_velocity=Vector3(
                x=ball.physics.angular_velocity.x,
                y=ball.physics.angular_velocity.y,
                z=ball.physics.angular_velocity.z
            )))
        elif isinstance(game_tick_packet, GameTickPacket.GameTickPacket):
            car_states = {}
            for i in range(game_tick_packet.PlayersLength()):
                car = game_tick_packet.Players(i)
                car_states[i] = CarState(physics=Physics(location=Vector3(
                    x=car.Physics().Location().X(),
                    y=car.Physics().Location().Y(),
                    z=car.Physics().Location().Z()
                ), rotation=Rotator(
                    pitch=car.Physics().Rotation().Pitch(),
                    yaw=car.Physics().Rotation().Yaw(),
                    roll=car.Physics().Rotation().Roll()
                ), velocity=Vector3(
                    x=car.Physics().Velocity().X(),
                    y=car.Physics().Velocity().Y(),
                    z=car.Physics().Velocity().Z()
                ), angular_velocity=Vector3(
                    x=car.Physics().AngularVelocity().X(),
                    y=car.Physics().AngularVelocity().Y(),
                    z=car.Physics().AngularVelocity().Z()
                )), boost_amount=car.Boost(), jumped=car.Jumped(), double_jumped=car.DoubleJumped())
            game_state.cars = car_states
            ball = game_tick_packet.Ball()
            game_state.ball = BallState(physics=Physics(location=Vector3(
                x=ball.Physics().Location().X(),
                y=ball.Physics().Location().Y(),
                z=ball.Physics().Location().Z()
            ), rotation=Rotator(
                pitch=ball.Physics().Rotation().Pitch(),
                yaw=ball.Physics().Rotation().Yaw(),
                roll=ball.Physics().Rotation().Roll()
            ), velocity=Vector3(
                x=ball.Physics().Velocity().X(),
                y=ball.Physics().Velocity().Y(),
                z=ball.Physics().Velocity().Z()
            ), angular_velocity=Vector3(
                x=ball.Physics().AngularVelocity().X(),
                y=ball.Physics().AngularVelocity().Y(),
                z=ball.Physics().AngularVelocity().Z()
            )))
        return game_state





