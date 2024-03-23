from direct.showbase.ShowBase import ShowBase
from direct.stdpy import threading2
from panda3d.core import load_prc_file_data, BitMask32, TransformState, ConfigVariableManager
from panda3d.core import FrameBufferProperties, AntialiasAttrib, InputDevice, Texture
import sys
import random
import time
from panda3d.core import LPoint3f, Point3, Vec2, Vec3, Vec4, LVecBase3f, VBase4, LPoint2f, NodePath
from panda3d.core import WindowProperties
from direct.showbase.DirectObject import DirectObject
from direct.interval.IntervalGlobal import *
# gui imports
from direct.gui.DirectGui import *
from panda3d.core import TextNode
# new pbr imports
import complexpbr
# local imports
import arena_lighting


class app(ShowBase):
    def __init__(self):
        load_prc_file_data("", """
            win-size 1920 1080
            window-title T U B E F A L L E R
            framebuffer-multisample 1
            multisamples 4
            hardware-animated-vertices #t
            cursor-hidden #t
            gl-depth-zero-to-one #f
            show-frame-rate-meter #t
        """)

        # initialize the showbase
        super().__init__()

        # lighting
        arena_lighting.lighting()
        arena_lighting.init_flashlight()
        self.accept('f', arena_lighting.toggle_flashlight)
        self.accept("gamepad-face_x", arena_lighting.toggle_flashlight)

        # complexpbr
        complexpbr.apply_shader(self.render, env_res=512)
        # complexpbr.set_cubebuff_inactive()
        
        def quality_mode():
            complexpbr.screenspace_init()
        
            base.screen_quad.set_shader_input("bloom_intensity", 0.7)
            base.screen_quad.set_shader_input("bloom_threshold", 0.7)
            base.screen_quad.set_shader_input("bloom_blur_width", 30)
            base.screen_quad.set_shader_input("bloom_samples", 6)
            base.screen_quad.set_shader_input('ssr_samples', 0)
            base.screen_quad.set_shader_input('ssr_intensity', 0)
            base.screen_quad.set_shader_input('ssao_samples', 6)
            base.screen_quad.set_shader_input('hsv_r', 1.0)
            base.screen_quad.set_shader_input('hsv_g', 1.1)
            base.screen_quad.set_shader_input('hsv_b', 1.0)

            text_1.set_text("Quality Mode: On")

        self.accept_once('m', quality_mode)
        self.accept_once("gamepad-face_y", quality_mode)

        def save_screen():
            base.screenshot('arena_screen')
            
        self.accept('o', save_screen)
        
        # window props
        props = WindowProperties()
        props.set_mouse_mode(WindowProperties.M_relative)
        base.win.request_properties(props)
        base.set_background_color(0.5, 0.5, 0.8)
        
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 15000)
        # ConfigVariableManager.getGlobalPtr().listVariables()

        self.accept("f3", self.toggle_wireframe)
        self.accept("escape", sys.exit, [0])
        
        self.game_start = 0
        
        # gamepad initialization
        self.gamepad = None
        devices = self.devices.get_devices(InputDevice.DeviceClass.gamepad)

        if int(str(devices)[0]) > 0:
            self.gamepad = devices[0]

        def do_nothing():
            print('Something should happen but I cannot effect it.')
            
        def gp_exit():
            sys.exit()[0]

        self.accept("gamepad-back", gp_exit)
        self.accept("gamepad-start", do_nothing)
        # self.accept("gamepad-face_x", do_nothing)
        # self.accept("gamepad-face_x-up", do_nothing)
        # self.accept("gamepad-face_a", do_nothing)
        # self.accept("gamepad-face_a-up", do_nothing)
        self.accept("gamepad-face_b", do_nothing)
        self.accept("gamepad-face_b-up", do_nothing)
        # self.accept("gamepad-face_y", do_nothing)
        # self.accept("gamepad-face_y-up", do_nothing)

        if int(str(devices)[0]) > 0:
            base.attach_input_device(self.gamepad, prefix="gamepad")
            
        self.right_trigger_val = 0.0
        self.left_trigger_val = 0.0
        # end gamepad initialization

        # begin physics environment
        from panda3d.bullet import BulletWorld
        from panda3d.bullet import BulletCharacterControllerNode
        from panda3d.bullet import ZUp
        from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
        from panda3d.bullet import BulletTriangleMesh
        from panda3d.bullet import BulletTriangleMeshShape
        from panda3d.bullet import BulletBoxShape, BulletSphereShape
        from panda3d.bullet import BulletGhostNode
        from panda3d.bullet import BulletRigidBodyNode
        from panda3d.bullet import BulletPlaneShape

        self.world = BulletWorld()
        # self.world.set_gravity(Vec3(0, 0, -9.81))
        self.world.set_gravity(Vec3(0, 0, -1.5))
        
        def make_collision_from_model(input_model, node_number, mass, world, target_pos, rigid_name='input_model_tri_mesh'):
            # tristrip generation from static models
            # generic tri-strip collision generator begins
            input_model.flatten_strong()
            geom_nodes = input_model.find_all_matches('**/+GeomNode')
            geom_nodes = geom_nodes.get_path(node_number).node()
            # print(geom_nodes)
            geom_target = geom_nodes.get_geom(0)
            # print(geom_target)
            output_bullet_mesh = BulletTriangleMesh()
            output_bullet_mesh.add_geom(geom_target)
            tri_shape = BulletTriangleMeshShape(output_bullet_mesh, dynamic=False)
            print(output_bullet_mesh)

            body = BulletRigidBodyNode(rigid_name)
            np = self.render.attach_new_node(body)
            np.node().add_shape(tri_shape)
            np.node().set_mass(mass)
            np.node().set_friction(0.01)
            np.node().set_ccd_motion_threshold(0.000000007)
            np.node().set_ccd_swept_sphere_radius(0.01)
            np.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
            np.set_pos(target_pos)
            np.set_scale(1)
            # np.set_h(180)
            # np.set_p(180)
            # np.set_r(180)
            np.set_collide_mask(BitMask32.allOn())
            world.attach_rigid_body(np.node())

        # directly make a text node to display text
        text_1 = TextNode('text_1_node')
        text_1.set_text("Quality Mode: Off  (Press 'm' to turn on.)")
        if int(str(devices)[0]) > 0:
            text_1.set_text("Quality Mode: Off  (Press 'Y' to turn on.)")
        # text_1.set_text("Quality Mode: Off  (Press 'm' to turn on.)")
        text_1_node = self.aspect2d.attach_new_node(text_1)
        text_1_node.set_scale(0.04)
        text_1_node.set_pos(-1.4, 0, 0.92)
        # import font and set pixels per unit font quality
        nunito_font = loader.load_font('fonts/Nunito/Nunito-Light.ttf')
        nunito_font.set_pixels_per_unit(100)
        nunito_font.set_page_size(512, 512)
        # apply font
        text_1.set_font(nunito_font)
        text_1.set_shadow(0.1)

        # directly make a text node to display text
        text_2 = TextNode('text_2_node')

        text_2.set_text("")
        text_2_node = self.aspect2d.attach_new_node(text_2)
        text_2_node.set_scale(0.04)
        text_2_node.set_pos(-1.4, 0, 0.8)
        # import font and set pixels per unit font quality
        nunito_font = self.loader.load_font('fonts/Nunito/Nunito-Light.ttf')
        nunito_font.set_pixels_per_unit(100)
        nunito_font.set_page_size(512, 512)
        # apply font
        text_2.set_font(nunito_font)
        text_2.set_text_color(0.9, 0.9, 0.9, 1)
        text_2.set_shadow(0.1)

        # 3D player movement system begins
        self.keyMap = {"left": 0, "right": 0, "forward": 0, "backward": 0, "run": 0, "jump": 0, "receiver_right": 0, "receiver_left": 0}

        def setKey(key, value):
            self.keyMap[key] = value

        # define button map
        self.accept("a", setKey, ["left", 1])
        self.accept("a-up", setKey, ["left", 0])
        self.accept("d", setKey, ["right", 1])
        self.accept("d-up", setKey, ["right", 0])
        self.accept("w", setKey, ["forward", 1])
        self.accept("w-up", setKey, ["forward", 0])
        self.accept("s", setKey, ["backward", 1])
        self.accept("s-up", setKey, ["backward", 0])
        self.accept("shift", setKey, ["run", 1])
        self.accept("shift-up", setKey, ["run", 0])
        self.accept("space", setKey, ["jump", 1])
        self.accept("space-up", setKey, ["jump", 0])
        self.accept("arrow_right", setKey, ["receiver_right", 1])
        self.accept("arrow_right-up", setKey, ["receiver_right", 0])
        self.accept("arrow_left", setKey, ["receiver_left", 1])
        self.accept("arrow_left-up", setKey, ["receiver_left", 0])
        # disable mouse
        self.disable_mouse()
        self.cam.set_pos(0,0,215)
        self.cam.look_at(0,0,-3000)

        def set_sun_1_task(Task):
            base.sun_1.set_z(self.cam.get_z() + 50)
                
            return Task.cont

        def set_sun_2_task(Task):
            base.sun_2.set_z(self.cam.get_z() + 50)
            
            return Task.cont

        # infinite ground plane
        # the effective world-Z limit
        ground_plane = BulletPlaneShape(Vec3(0, 0, 1), 0)
        node = BulletRigidBodyNode('ground')
        node.add_shape(ground_plane)
        node.set_friction(0.1)
        np = self.render.attach_new_node(node)
        np.set_pos(0, 0, -2000)
        self.world.attach_rigid_body(node)

        def level_1():
            def spawn_receiver_group():
                # dropped cylinders test
                special_shape_x = 1
                special_shape_y = 10
                special_mass = 500
                d_coll_pos = Vec3(0,0,100)
                
                large_cylinders = [Vec3(10,0,100),Vec3(0,-10,100),Vec3(0,10,100),Vec3(-10,0,100)]
                medium_cylinders = [Vec3(2,2,100),Vec3(2,-2,100),Vec3(-2,2,100),Vec3(-2,-2,100)]
                small_cylinders = [Vec3(17,0,100),Vec3(-17,0,100),Vec3(0,17,100),Vec3(0,-17,100)]

                # 4x large cylinder (middle group)
                # 4x medium cylinder (center group)
                # 4x small cylinder (outside edges)
                
                for cyl_pos in large_cylinders:
                    special_shape_x = 1
                    special_shape_y = 10
                    special_mass = 500

                    # dynamic collision
                    special_shape = BulletCylinderShape(special_shape_x, special_shape_y, ZUp)
                    # rigidbody
                    body = BulletRigidBodyNode('random_prisms')
                    d_coll = self.render.attach_new_node(body)
                    d_coll.node().add_shape(special_shape)
                    d_coll.node().set_mass(special_mass)
                    d_coll.node().set_friction(50)
                    d_coll.set_collide_mask(BitMask32.allOn())
                    # turn on Continuous Collision Detection
                    d_coll.node().set_ccd_motion_threshold(0.000000007)
                    d_coll.node().set_ccd_swept_sphere_radius(0.01)
                    d_coll.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
                    d_coll.set_pos(cyl_pos)
                    box_model = self.loader.load_model('models/' + 'dropping_cylinder_2by10' + '.bam')
                    # box_model.reparent_to(self.render)
                    box_model.copy_to(d_coll)
                    # box_model.set_pos(0,0,-1)

                    dis_tex = Texture()
                    dis_tex.read('textures/Metal041A_2K-PNG/Metal041A_2K_Displacement.png')
                    box_model.set_shader_input('displacement_map', dis_tex)
                    box_model.set_shader_input('displacement_scale', 0.03)
                    
                    self.world.attach_rigid_body(d_coll.node())

                for cyl_pos in medium_cylinders:
                    special_shape_x = 0.3  # 0.5
                    special_shape_y = 10
                    special_mass = 250

                    # dynamic collision
                    special_shape = BulletCylinderShape(special_shape_x, special_shape_y, ZUp)
                    # rigidbody
                    body = BulletRigidBodyNode('random_prisms')
                    d_coll = self.render.attach_new_node(body)
                    d_coll.node().add_shape(special_shape)
                    d_coll.node().set_mass(special_mass)
                    d_coll.node().set_friction(50)
                    d_coll.set_collide_mask(BitMask32.allOn())
                    # turn on Continuous Collision Detection
                    d_coll.node().set_ccd_motion_threshold(0.000000007)
                    d_coll.node().set_ccd_swept_sphere_radius(0.01)
                    d_coll.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
                    d_coll.set_pos(cyl_pos)
                    box_model = self.loader.load_model('models/' + 'dropping_cylinder_1by10' + '.bam')
                    # box_model.reparent_to(self.render)
                    box_model.copy_to(d_coll)
                    # box_model.set_pos(0,0,-1)

                    dis_tex = Texture()
                    dis_tex.read('textures/Metal041A_2K-PNG/Metal041A_2K_Displacement.png')
                    box_model.set_shader_input('displacement_map', dis_tex)
                    box_model.set_shader_input('displacement_scale', 0.03)
                    
                    self.world.attach_rigid_body(d_coll.node())

                for cyl_pos in small_cylinders:
                    special_shape_x = 0.15  # 0.25
                    special_shape_y = 10
                    special_mass = 125

                    # dynamic collision
                    special_shape = BulletCylinderShape(special_shape_x, special_shape_y, ZUp)
                    # rigidbody
                    body = BulletRigidBodyNode('random_prisms')
                    d_coll = self.render.attach_new_node(body)
                    d_coll.node().add_shape(special_shape)
                    d_coll.node().set_mass(special_mass)
                    d_coll.node().set_friction(50)
                    d_coll.set_collide_mask(BitMask32.allOn())
                    # turn on Continuous Collision Detection
                    d_coll.node().set_ccd_motion_threshold(0.000000007)
                    d_coll.node().set_ccd_swept_sphere_radius(0.01)
                    d_coll.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
                    d_coll.set_pos(cyl_pos)
                    box_model = self.loader.load_model('models/' + 'dropping_cylinder_05by10' + '.bam')
                    # box_model.reparent_to(self.render)
                    box_model.copy_to(d_coll)
                    # box_model.set_pos(0,0,-1)

                    dis_tex = Texture()
                    dis_tex.read('textures/Metal041A_2K-PNG/Metal041A_2K_Displacement.png')
                    box_model.set_shader_input('displacement_map', dis_tex)
                    box_model.set_shader_input('displacement_scale', 0.03)
                    
                    self.world.attach_rigid_body(d_coll.node())

            spawn_receiver_group()
            '''
            # tube level surround
            tube_level = self.loader.load_model('models/metal_tube_large.glb')
            tube_level.reparent_to(self.render)
            tube_level.set_pos(0, 0, -2800)
            # tube_level.set_h(40)
            self.tube_level = tube_level
            self.tube_level.set_light(base.tube_light_1)
            dis_tex = Texture()
            dis_tex.read('textures/Metal045A_2K-PNG/Metal045A_2K-PNG_Displacement.png')
            self.tube_level.set_shader_input('displacement_map', dis_tex)
            self.tube_level.set_shader_input('displacement_scale', 0.03)
            '''
            # receiver instantiation
            test_receiver_1 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_1.reparent_to(self.render)
            test_receiver_1.set_pos(0, 0, 0)
            test_receiver_1.set_h(40)
            self.test_receiver_1 = test_receiver_1

            make_collision_from_model(test_receiver_1, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_1')  # target_pos is zeroed due to flattening
            test_receiver_1_coll = self.render.find('**/test_receiver_1')
            self.test_receiver_1_coll = test_receiver_1_coll

            test_receiver_2 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_2.reparent_to(self.render)
            test_receiver_2.set_pos(0, 0, -100)
            test_receiver_2.set_h(20)
            self.test_receiver_2 = test_receiver_2

            make_collision_from_model(test_receiver_2, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_2')  # target_pos is zeroed due to flattening
            test_receiver_2_coll = self.render.find('**/test_receiver_2')
            self.test_receiver_2_coll = test_receiver_2_coll
            
            test_receiver_3 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_3.reparent_to(self.render)
            test_receiver_3.set_pos(0, 0, -300)
            test_receiver_3.set_h(25)
            self.test_receiver_3 = test_receiver_3

            make_collision_from_model(test_receiver_3, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_3')  # target_pos is zeroed due to flattening
            test_receiver_3_coll = self.render.find('**/test_receiver_3')
            self.test_receiver_3_coll = test_receiver_3_coll

            test_receiver_4 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_4.reparent_to(self.render)
            test_receiver_4.set_pos(0, 0, -500)
            test_receiver_4.set_h(36)
            self.test_receiver_4 = test_receiver_4

            make_collision_from_model(test_receiver_4, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_4')  # target_pos is zeroed due to flattening
            test_receiver_4_coll = self.render.find('**/test_receiver_4')
            self.test_receiver_4_coll = test_receiver_4_coll
            
            test_receiver_5 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_5.reparent_to(self.render)
            test_receiver_5.set_pos(0, 0, -650)
            test_receiver_5.set_h(27)
            self.test_receiver_5 = test_receiver_5

            make_collision_from_model(test_receiver_5, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_5')  # target_pos is zeroed due to flattening
            test_receiver_5_coll = self.render.find('**/test_receiver_5')
            self.test_receiver_5_coll = test_receiver_5_coll
            
            test_receiver_6 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_6.reparent_to(self.render)
            test_receiver_6.set_pos(0, 0, -800)
            test_receiver_6.set_h(17)
            self.test_receiver_6 = test_receiver_6

            make_collision_from_model(test_receiver_6, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_6')  # target_pos is zeroed due to flattening
            test_receiver_6_coll = self.render.find('**/test_receiver_6')
            self.test_receiver_6_coll = test_receiver_6_coll

            test_receiver_7 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_7.reparent_to(self.render)
            test_receiver_7.set_pos(0, 0, -1000)
            test_receiver_7.set_h(52)
            self.test_receiver_7 = test_receiver_7

            make_collision_from_model(test_receiver_7, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_7')  # target_pos is zeroed due to flattening
            test_receiver_7_coll = self.render.find('**/test_receiver_7')
            self.test_receiver_7_coll = test_receiver_7_coll
            
            test_receiver_8 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_8.reparent_to(self.render)
            test_receiver_8.set_pos(0, 0, -1300)
            test_receiver_8.set_h(62)
            self.test_receiver_8 = test_receiver_8

            make_collision_from_model(test_receiver_8, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_8')  # target_pos is zeroed due to flattening
            test_receiver_8_coll = self.render.find('**/test_receiver_8')
            self.test_receiver_8_coll = test_receiver_8_coll

            test_receiver_9 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_9.reparent_to(self.render)
            test_receiver_9.set_pos(0, 0, -1600)
            test_receiver_9.set_h(12)
            self.test_receiver_9 = test_receiver_9

            make_collision_from_model(test_receiver_9, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_9')  # target_pos is zeroed due to flattening
            test_receiver_9_coll = self.render.find('**/test_receiver_9')
            self.test_receiver_9_coll = test_receiver_9_coll

            self.cleanup_count = 1

            def cleanup_level():
                self.test_receiver_1.show()
                self.test_receiver_2.show()
                self.test_receiver_3.show()
                self.test_receiver_4.show()
                self.test_receiver_5.show()
                self.test_receiver_6.show()
                self.test_receiver_7.show()
                self.test_receiver_8.show()
                self.test_receiver_9.show()

                self.test_receiver_1.set_h(0)
                self.test_receiver_2.set_h(0)
                self.test_receiver_3.set_h(0)
                self.test_receiver_4.set_h(0)
                self.test_receiver_5.set_h(0)
                self.test_receiver_6.set_h(0)
                self.test_receiver_7.set_h(0)
                self.test_receiver_8.set_h(0)
                self.test_receiver_9.set_h(0)
                
                for cyl in self.render.find_all_matches('**/random_prisms*'):
                    cyl.detach_node()
                    self.world.remove(cyl.node())
                    del cyl

                for tr in self.render.find_all_matches('**/test_receiver_*'):
                    tr.detach_node()
                    self.world.remove(tr.node())
                    del tr

                spawn_receiver_group()

                make_collision_from_model(test_receiver_1, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_1')
                test_receiver_1_coll = self.render.find('**/test_receiver_1')
                self.test_receiver_1_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_2, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_2')
                test_receiver_1_coll = self.render.find('**/test_receiver_2')
                self.test_receiver_2_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_3, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_3')
                test_receiver_1_coll = self.render.find('**/test_receiver_3')
                self.test_receiver_3_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_4, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_4')
                test_receiver_1_coll = self.render.find('**/test_receiver_4')
                self.test_receiver_4_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_5, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_5')
                test_receiver_1_coll = self.render.find('**/test_receiver_5')
                self.test_receiver_5_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_6, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_6')
                test_receiver_1_coll = self.render.find('**/test_receiver_6')
                self.test_receiver_6_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_7, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_7')
                test_receiver_1_coll = self.render.find('**/test_receiver_7')
                self.test_receiver_7_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_8, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_8')
                test_receiver_1_coll = self.render.find('**/test_receiver_8')
                self.test_receiver_8_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_9, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_9')
                test_receiver_1_coll = self.render.find('**/test_receiver_9')
                self.test_receiver_9_coll = test_receiver_1_coll

                self.reference_cyl = self.render.find_all_matches('**/random_prisms*')[9 * self.cleanup_count]
            
                self.cam.set_pos(0,0,150)
                
            self.accept('p', cleanup_level)

            self.x_offset = 5
            self.y_offset = 5
            self.control_text = '\nRotate Receiver: Arrow L/R \nPan Camera: WASD'

            def detect_end_game(current_receiver):
                active_cylinders = self.render.find_all_matches('**/random_prisms*')
                total_contacts = 0

                for cyl in active_cylinders:
                    body_1 = cyl
                    body_2 = current_receiver

                    contact_result = self.world.contact_test(current_receiver)

                    for contact in contact_result.get_contacts():
                        total_contacts += 1

                if total_contacts > 1:
                    text_1.set_text("Contacts detected, you lost the game.\nPress 'p' to restart.")

                return total_contacts

            def rotate_receiver(Task):
                delay_time = 0.02
                Task.delay_time = delay_time

                reference_z = self.render.find_all_matches('**/random_prisms*')[0].get_z()
                
                if reference_z > 0:
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_1.get_h()
                        receiver_coll_h = self.test_receiver_1_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_1,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_1_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_1.get_h()
                        receiver_coll_h = self.test_receiver_1_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_1,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_1_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_1.get_h(), 1)))
                                                                      + '\n' + 'Target: 40' + self.control_text)

                    end_game_result = detect_end_game(self.test_receiver_1_coll.node())
                    if end_game_result > 0:
                        # cleanup_level()
                        pass
                        
                if reference_z < -10 > -100:
                    self.test_receiver_1.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_2.get_h()
                        receiver_coll_h = self.test_receiver_2_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_2,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_2_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_2.get_h()
                        receiver_coll_h = self.test_receiver_2_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_2,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_2_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_2.get_h(), 1)))
                                                                      + '\n' + 'Target: 20' + self.control_text)

                    end_game_result = detect_end_game(self.test_receiver_2_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                    
                if reference_z < -110 > -310:
                    self.test_receiver_2.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_3.get_h()
                        receiver_coll_h = self.test_receiver_3_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_3,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_3_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_3.get_h()
                        receiver_coll_h = self.test_receiver_3_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_3,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_3_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_3.get_h(), 1)))
                                                                      + '\n' + 'Target: 25')

                    end_game_result = detect_end_game(self.test_receiver_3_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                                                                      
                if reference_z < -310 > -510:
                    self.test_receiver_3.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_4.get_h()
                        receiver_coll_h = self.test_receiver_4_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_4,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_4_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_4.get_h()
                        receiver_coll_h = self.test_receiver_4_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_4,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_4_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_4.get_h(), 1)))
                                                                      + '\n' + 'Target: 36')

                    end_game_result = detect_end_game(self.test_receiver_4_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                                                                      
                if reference_z < -510 > -660:
                    self.test_receiver_4.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_5.get_h()
                        receiver_coll_h = self.test_receiver_5_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_5,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_5_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_5.get_h()
                        receiver_coll_h = self.test_receiver_5_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_5,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_5_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_5.get_h(), 1)))
                                                                      + '\n' + 'Target: 27')

                    end_game_result = detect_end_game(self.test_receiver_5_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                                                                      
                if reference_z < -660 > -810:
                    self.test_receiver_5.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_6.get_h()
                        receiver_coll_h = self.test_receiver_6_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_6,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_6_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_6.get_h()
                        receiver_coll_h = self.test_receiver_6_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_6,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_6_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_6_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 17')

                    end_game_result = detect_end_game(self.test_receiver_6_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -810 > -1010:
                    self.test_receiver_6.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_7.get_h()
                        receiver_coll_h = self.test_receiver_7_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_7,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_7_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_7.get_h()
                        receiver_coll_h = self.test_receiver_7_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_7,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_7_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_7_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 52')

                    end_game_result = detect_end_game(self.test_receiver_7_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -1010 > -1310:
                    self.test_receiver_7.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_8.get_h()
                        receiver_coll_h = self.test_receiver_8_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_8,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_8_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_8.get_h()
                        receiver_coll_h = self.test_receiver_8_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_8,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_8_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_8_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 62')

                    end_game_result = detect_end_game(self.test_receiver_8_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -1310 > -1610:
                    self.test_receiver_8.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_9.get_h()
                        receiver_coll_h = self.test_receiver_9_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_9,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_9_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_9.get_h()
                        receiver_coll_h = self.test_receiver_9_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_9,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_9_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_9_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 12')

                    end_game_result = detect_end_game(self.test_receiver_9_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -1610:
                    print('Game win state passed.')

                return Task.again

            self.fall_factor = 50
            self.reference_cyl = self.render.find_all_matches('**/random_prisms*')[0]
            self.rc_z_1 = 0
            self.rc_z_2 = 0
            self.rc_speed = 0

            def measure_fall_speed(Task):
                Task.delay_time = 1

                if self.rc_z_1 == 0:
                    self.rc_z_1 = self.reference_cyl.get_z()
                elif abs(self.rc_z_1) > 0:
                    self.rc_z_2 = self.reference_cyl.get_z()
                    self.rc_speed = abs(self.rc_z_1 - self.rc_z_2)
                    self.rc_z_1 = 0

                # print(self.render.find_all_matches('**/random_prisms*')[0].get_z())
                # print(self.reference_cyl.get_z())

                return Task.again

            def update_receiver_cam(Task):
                dt = globalClock.get_dt()
                max_dist = 20
                z_offset = 20
                cam_z = self.cam.get_z()

                reference_z = self.reference_cyl.get_z()
                abs_z = abs(cam_z - reference_z)
                avg_fr = globalClock.get_average_frame_rate()
                if avg_fr == 0:
                    avg_fr = 1

                if abs_z > 30 < 60:
                    self.fall_factor *= dt
                    self.fall_factor += self.rc_speed / avg_fr
                if abs_z < 15:
                    self.fall_factor *= dt
                    self.fall_factor -= self.rc_speed / (avg_fr/2)

                falling_z = self.cam.get_z() - self.fall_factor
                self.cam.set_pos(self.x_offset, self.y_offset, falling_z)
                # self.cam.look_at(active_cylinders[0])
                base.tube_light_1.set_pos(self.cam.get_pos())

                if self.keyMap["right"]:
                    if self.x_offset <= max_dist:
                        self.x_offset += 0.1

                if self.keyMap["left"]:
                    if self.x_offset >= -max_dist:
                        self.x_offset -= 0.1

                if self.keyMap["forward"]:
                    if self.y_offset <= max_dist:
                        self.y_offset += 0.1

                if self.keyMap["backward"]:
                    if self.y_offset >= -max_dist:
                        self.y_offset -= 0.1

                if cam_z > 1690 or cam_z < reference_z:
                    text_1.set_text('Recovering level...')
                    cleanup_level()

                return Task.cont
                
            self.task_mgr.add(rotate_receiver)
            self.task_mgr.add(update_receiver_cam)
            self.task_mgr.add(measure_fall_speed)
            
        # level_1()

        def intro_sequence():
            def spawn_receiver_group():
                # dropped cylinders test
                special_shape_x = 1
                special_shape_y = 10
                special_mass = 500
                d_coll_pos = Vec3(0,0,100)
                
                large_cylinders = [Vec3(10,0,100),Vec3(0,-10,100),Vec3(0,10,100),Vec3(-10,0,100)]
                medium_cylinders = [Vec3(2,2,100),Vec3(2,-2,100),Vec3(-2,2,100),Vec3(-2,-2,100)]
                small_cylinders = [Vec3(17,0,100),Vec3(-17,0,100),Vec3(0,17,100),Vec3(0,-17,100)]

                large_cylinder = self.loader.load_model('models/' + 'dropping_cylinder_2by10' + '.bam')
                # large_cylinder.write_bam_file("dropping_cylinder_2by10.bam")
                medium_cylinder = self.loader.load_model('models/' + 'dropping_cylinder_1by10' + '.bam')
                # medium_cylinder.write_bam_file("dropping_cylinder_1by10.bam")
                small_cylinder = self.loader.load_model('models/' + 'dropping_cylinder_05by10' + '.bam')
                # small_cylinder.write_bam_file("dropping_cylinder_05by10.bam")

                # 4x large cylinder (middle group)
                # 4x medium cylinder (center group)
                # 4x small cylinder (outside edges)
                
                for cyl_pos in large_cylinders:
                    special_shape_x = 1
                    special_shape_y = 10
                    special_mass = 500

                    # dynamic collision
                    special_shape = BulletCylinderShape(special_shape_x, special_shape_y, ZUp)
                    # rigidbody
                    body = BulletRigidBodyNode('random_prisms')
                    d_coll = self.render.attach_new_node(body)
                    d_coll.node().add_shape(special_shape)
                    d_coll.node().set_mass(special_mass)
                    d_coll.node().set_friction(50)
                    d_coll.set_collide_mask(BitMask32.allOn())
                    # turn on Continuous Collision Detection
                    d_coll.node().set_ccd_motion_threshold(0.000000007)
                    d_coll.node().set_ccd_swept_sphere_radius(0.01)
                    d_coll.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
                    d_coll.set_pos(cyl_pos)
                    box_model = large_cylinder
                    # box_model.reparent_to(self.render)
                    box_model.copy_to(d_coll)
                    # box_model.set_pos(0,0,-1)

                    dis_tex = Texture()
                    dis_tex.read('textures/Metal041A_2K-PNG/Metal041A_2K_Displacement.png')
                    box_model.set_shader_input('displacement_map', dis_tex)
                    box_model.set_shader_input('displacement_scale', 0.03)
                    
                    self.world.attach_rigid_body(d_coll.node())

                for cyl_pos in medium_cylinders:
                    special_shape_x = 0.3  # 0.5
                    special_shape_y = 10
                    special_mass = 250

                    # dynamic collision
                    special_shape = BulletCylinderShape(special_shape_x, special_shape_y, ZUp)
                    # rigidbody
                    body = BulletRigidBodyNode('random_prisms')
                    d_coll = self.render.attach_new_node(body)
                    d_coll.node().add_shape(special_shape)
                    d_coll.node().set_mass(special_mass)
                    d_coll.node().set_friction(50)
                    d_coll.set_collide_mask(BitMask32.allOn())
                    # turn on Continuous Collision Detection
                    d_coll.node().set_ccd_motion_threshold(0.000000007)
                    d_coll.node().set_ccd_swept_sphere_radius(0.01)
                    d_coll.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
                    d_coll.set_pos(cyl_pos)
                    box_model = medium_cylinder
                    # box_model.reparent_to(self.render)
                    box_model.copy_to(d_coll)
                    # box_model.set_pos(0,0,-1)

                    dis_tex = Texture()
                    dis_tex.read('textures/Metal041A_2K-PNG/Metal041A_2K_Displacement.png')
                    box_model.set_shader_input('displacement_map', dis_tex)
                    box_model.set_shader_input('displacement_scale', 0.03)
                    
                    self.world.attach_rigid_body(d_coll.node())

                for cyl_pos in small_cylinders:
                    special_shape_x = 0.15  # 0.25
                    special_shape_y = 10
                    special_mass = 125

                    # dynamic collision
                    special_shape = BulletCylinderShape(special_shape_x, special_shape_y, ZUp)
                    # rigidbody
                    body = BulletRigidBodyNode('random_prisms')
                    d_coll = self.render.attach_new_node(body)
                    d_coll.node().add_shape(special_shape)
                    d_coll.node().set_mass(special_mass)
                    d_coll.node().set_friction(50)
                    d_coll.set_collide_mask(BitMask32.allOn())
                    # turn on Continuous Collision Detection
                    d_coll.node().set_ccd_motion_threshold(0.000000007)
                    d_coll.node().set_ccd_swept_sphere_radius(0.01)
                    d_coll.node().set_deactivation_enabled(False)  # prevents stopping the physics simulation
                    d_coll.set_pos(cyl_pos)
                    box_model = small_cylinder
                    # box_model.reparent_to(self.render)
                    box_model.copy_to(d_coll)
                    # box_model.set_pos(0,0,-1)

                    dis_tex = Texture()
                    dis_tex.read('textures/Metal041A_2K-PNG/Metal041A_2K_Displacement.png')
                    box_model.set_shader_input('displacement_map', dis_tex)
                    box_model.set_shader_input('displacement_scale', 0.03)
                    
                    self.world.attach_rigid_body(d_coll.node())

            spawn_receiver_group()
            '''
            # tube level surround
            tube_level = self.loader.load_model('models/metal_tube_large.glb')
            tube_level.reparent_to(self.render)
            tube_level.set_pos(0, 0, -2800)
            # tube_level.set_h(40)
            self.tube_level = tube_level
            self.tube_level.set_light(base.tube_light_1)
            dis_tex = Texture()
            dis_tex.read('textures/Metal045A_2K-PNG/Metal045A_2K-PNG_Displacement.png')
            self.tube_level.set_shader_input('displacement_map', dis_tex)
            self.tube_level.set_shader_input('displacement_scale', 0.03)
            '''
            # receiver instantiation
            test_receiver_1 = self.loader.load_model('models/test_receiver_2.bam')
            # test_receiver_1.write_bam_file("test_receiver_2.bam")
            test_receiver_1.reparent_to(self.render)
            test_receiver_1.set_pos(0, 0, 0)
            test_receiver_1.set_h(40)
            self.test_receiver_1 = test_receiver_1

            make_collision_from_model(test_receiver_1, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_1')  # target_pos is zeroed due to flattening
            test_receiver_1_coll = self.render.find('**/test_receiver_1')
            self.test_receiver_1_coll = test_receiver_1_coll

            test_receiver_2 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_2.reparent_to(self.render)
            test_receiver_2.set_pos(0, 0, -100)
            test_receiver_2.set_h(20)
            self.test_receiver_2 = test_receiver_2

            make_collision_from_model(test_receiver_2, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_2')  # target_pos is zeroed due to flattening
            test_receiver_2_coll = self.render.find('**/test_receiver_2')
            self.test_receiver_2_coll = test_receiver_2_coll
            
            test_receiver_3 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_3.reparent_to(self.render)
            test_receiver_3.set_pos(0, 0, -300)
            test_receiver_3.set_h(25)
            self.test_receiver_3 = test_receiver_3

            make_collision_from_model(test_receiver_3, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_3')  # target_pos is zeroed due to flattening
            test_receiver_3_coll = self.render.find('**/test_receiver_3')
            self.test_receiver_3_coll = test_receiver_3_coll

            test_receiver_4 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_4.reparent_to(self.render)
            test_receiver_4.set_pos(0, 0, -500)
            test_receiver_4.set_h(36)
            self.test_receiver_4 = test_receiver_4

            make_collision_from_model(test_receiver_4, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_4')  # target_pos is zeroed due to flattening
            test_receiver_4_coll = self.render.find('**/test_receiver_4')
            self.test_receiver_4_coll = test_receiver_4_coll
            
            test_receiver_5 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_5.reparent_to(self.render)
            test_receiver_5.set_pos(0, 0, -650)
            test_receiver_5.set_h(27)
            self.test_receiver_5 = test_receiver_5

            make_collision_from_model(test_receiver_5, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_5')  # target_pos is zeroed due to flattening
            test_receiver_5_coll = self.render.find('**/test_receiver_5')
            self.test_receiver_5_coll = test_receiver_5_coll
            
            test_receiver_6 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_6.reparent_to(self.render)
            test_receiver_6.set_pos(0, 0, -800)
            test_receiver_6.set_h(17)
            self.test_receiver_6 = test_receiver_6

            make_collision_from_model(test_receiver_6, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_6')  # target_pos is zeroed due to flattening
            test_receiver_6_coll = self.render.find('**/test_receiver_6')
            self.test_receiver_6_coll = test_receiver_6_coll

            test_receiver_7 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_7.reparent_to(self.render)
            test_receiver_7.set_pos(0, 0, -1000)
            test_receiver_7.set_h(52)
            self.test_receiver_7 = test_receiver_7

            make_collision_from_model(test_receiver_7, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_7')  # target_pos is zeroed due to flattening
            test_receiver_7_coll = self.render.find('**/test_receiver_7')
            self.test_receiver_7_coll = test_receiver_7_coll
            
            test_receiver_8 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_8.reparent_to(self.render)
            test_receiver_8.set_pos(0, 0, -1300)
            test_receiver_8.set_h(62)
            self.test_receiver_8 = test_receiver_8

            make_collision_from_model(test_receiver_8, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_8')  # target_pos is zeroed due to flattening
            test_receiver_8_coll = self.render.find('**/test_receiver_8')
            self.test_receiver_8_coll = test_receiver_8_coll

            test_receiver_9 = self.loader.load_model('models/test_receiver_2.bam')
            test_receiver_9.reparent_to(self.render)
            test_receiver_9.set_pos(0, 0, -1600)
            test_receiver_9.set_h(12)
            self.test_receiver_9 = test_receiver_9

            make_collision_from_model(test_receiver_9, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_9')  # target_pos is zeroed due to flattening
            test_receiver_9_coll = self.render.find('**/test_receiver_9')
            self.test_receiver_9_coll = test_receiver_9_coll

            self.cleanup_count = 1

            def cleanup_level():
                self.test_receiver_1.show()
                self.test_receiver_2.show()
                self.test_receiver_3.show()
                self.test_receiver_4.show()
                self.test_receiver_5.show()
                self.test_receiver_6.show()
                self.test_receiver_7.show()
                self.test_receiver_8.show()
                self.test_receiver_9.show()

                self.test_receiver_1.set_h(0)
                self.test_receiver_2.set_h(0)
                self.test_receiver_3.set_h(0)
                self.test_receiver_4.set_h(0)
                self.test_receiver_5.set_h(0)
                self.test_receiver_6.set_h(0)
                self.test_receiver_7.set_h(0)
                self.test_receiver_8.set_h(0)
                self.test_receiver_9.set_h(0)
                
                for cyl in self.render.find_all_matches('**/random_prisms*'):
                    cyl.detach_node()
                    self.world.remove(cyl.node())
                    del cyl

                for tr in self.render.find_all_matches('**/test_receiver_*'):
                    tr.detach_node()
                    self.world.remove(tr.node())
                    del tr

                spawn_receiver_group()

                make_collision_from_model(test_receiver_1, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_1')
                test_receiver_1_coll = self.render.find('**/test_receiver_1')
                self.test_receiver_1_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_2, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_2')
                test_receiver_1_coll = self.render.find('**/test_receiver_2')
                self.test_receiver_2_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_3, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_3')
                test_receiver_1_coll = self.render.find('**/test_receiver_3')
                self.test_receiver_3_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_4, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_4')
                test_receiver_1_coll = self.render.find('**/test_receiver_4')
                self.test_receiver_4_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_5, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_5')
                test_receiver_1_coll = self.render.find('**/test_receiver_5')
                self.test_receiver_5_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_6, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_6')
                test_receiver_1_coll = self.render.find('**/test_receiver_6')
                self.test_receiver_6_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_7, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_7')
                test_receiver_1_coll = self.render.find('**/test_receiver_7')
                self.test_receiver_7_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_8, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_8')
                test_receiver_1_coll = self.render.find('**/test_receiver_8')
                self.test_receiver_8_coll = test_receiver_1_coll

                make_collision_from_model(test_receiver_9, 0, 0, self.world, Vec3(0,0,0), 'test_receiver_9')
                test_receiver_1_coll = self.render.find('**/test_receiver_9')
                self.test_receiver_9_coll = test_receiver_1_coll

                self.reference_cyl = self.render.find_all_matches('**/random_prisms*')[9 * self.cleanup_count]
            
                self.cam.set_pos(0,0,150)
                
            self.accept('p', cleanup_level)

            self.x_offset = 5
            self.y_offset = 5
            self.control_text = '\nRotate Receiver: Arrow L/R \nPan Camera: WASD'

            def detect_end_game(current_receiver):
                active_cylinders = self.render.find_all_matches('**/random_prisms*')
                total_contacts = 0

                for cyl in active_cylinders:
                    body_1 = cyl
                    body_2 = current_receiver

                    contact_result = self.world.contact_test(current_receiver)

                    for contact in contact_result.get_contacts():
                        total_contacts += 1

                if total_contacts > 1:
                    text_1.set_text("Contacts detected, you lost the game.\nPress 'p' to restart.")

                return total_contacts

            def rotate_receiver(Task):
                delay_time = 0.02
                Task.delay_time = delay_time

                reference_z = self.render.find_all_matches('**/random_prisms*')[0].get_z()
                
                if reference_z > 0:
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_1.get_h()
                        receiver_coll_h = self.test_receiver_1_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_1,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_1_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_1.get_h()
                        receiver_coll_h = self.test_receiver_1_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_1,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_1_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_1.get_h(), 1)))
                                                                      + '\n' + 'Target: 40' + self.control_text)

                    end_game_result = detect_end_game(self.test_receiver_1_coll.node())
                    if end_game_result > 0:
                        # cleanup_level()
                        pass
                        
                if reference_z < -10 > -100:
                    self.test_receiver_1.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_2.get_h()
                        receiver_coll_h = self.test_receiver_2_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_2,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_2_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_2.get_h()
                        receiver_coll_h = self.test_receiver_2_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_2,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_2_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_2.get_h(), 1)))
                                                                      + '\n' + 'Target: 20' + self.control_text)

                    end_game_result = detect_end_game(self.test_receiver_2_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                    
                if reference_z < -110 > -310:
                    self.test_receiver_2.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_3.get_h()
                        receiver_coll_h = self.test_receiver_3_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_3,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_3_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_3.get_h()
                        receiver_coll_h = self.test_receiver_3_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_3,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_3_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_3.get_h(), 1)))
                                                                      + '\n' + 'Target: 25')

                    end_game_result = detect_end_game(self.test_receiver_3_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                                                                      
                if reference_z < -310 > -510:
                    self.test_receiver_3.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_4.get_h()
                        receiver_coll_h = self.test_receiver_4_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_4,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_4_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_4.get_h()
                        receiver_coll_h = self.test_receiver_4_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_4,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_4_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_4.get_h(), 1)))
                                                                      + '\n' + 'Target: 36')

                    end_game_result = detect_end_game(self.test_receiver_4_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                                                                      
                if reference_z < -510 > -660:
                    self.test_receiver_4.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_5.get_h()
                        receiver_coll_h = self.test_receiver_5_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_5,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_5_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_5.get_h()
                        receiver_coll_h = self.test_receiver_5_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_5,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_5_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_5.get_h(), 1)))
                                                                      + '\n' + 'Target: 27')

                    end_game_result = detect_end_game(self.test_receiver_5_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                                                                      
                if reference_z < -660 > -810:
                    self.test_receiver_5.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_6.get_h()
                        receiver_coll_h = self.test_receiver_6_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_6,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_6_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_6.get_h()
                        receiver_coll_h = self.test_receiver_6_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_6,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_6_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_6_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 17')

                    end_game_result = detect_end_game(self.test_receiver_6_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -810 > -1010:
                    self.test_receiver_6.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_7.get_h()
                        receiver_coll_h = self.test_receiver_7_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_7,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_7_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_7.get_h()
                        receiver_coll_h = self.test_receiver_7_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_7,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_7_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_7_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 52')

                    end_game_result = detect_end_game(self.test_receiver_7_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -1010 > -1310:
                    self.test_receiver_7.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_8.get_h()
                        receiver_coll_h = self.test_receiver_8_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_8,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_8_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_8.get_h()
                        receiver_coll_h = self.test_receiver_8_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_8,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_8_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_8_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 62')

                    end_game_result = detect_end_game(self.test_receiver_8_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -1310 > -1610:
                    self.test_receiver_8.hide()
                    if self.keyMap["receiver_right"]:
                        receiver_h = self.test_receiver_9.get_h()
                        receiver_coll_h = self.test_receiver_9_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_9,0.01,(receiver_h-1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_9_coll,0.01,(receiver_coll_h-1,0,0)).start()

                    if self.keyMap["receiver_left"]:
                        receiver_h = self.test_receiver_9.get_h()
                        receiver_coll_h = self.test_receiver_9_coll.get_h()
                        increment_receiver = LerpHprInterval(self.test_receiver_9,0.01,(receiver_h+1,0,0)).start()
                        increment_receiver_coll = LerpHprInterval(self.test_receiver_9_coll,0.01,(receiver_coll_h+1,0,0)).start()

                    text_1.set_text('Receiver Rotation Value: ' + str(abs(round(self.test_receiver_9_coll.get_h(), 1)))
                                                                      + '\n' + 'Target: 12')

                    end_game_result = detect_end_game(self.test_receiver_9_coll.node())
                    if end_game_result > 0:
                        # print(end_game_result)
                        pass
                        
                if reference_z < -1610:
                    print('Game win state passed.')

                return Task.again

            self.fall_factor = 50
            self.reference_cyl = self.render.find_all_matches('**/random_prisms*')[0]
            self.rc_z_1 = 0
            self.rc_z_2 = 0
            self.rc_speed = 0

            def measure_fall_speed(Task):
                Task.delay_time = 1

                if self.rc_z_1 == 0:
                    self.rc_z_1 = self.reference_cyl.get_z()
                elif abs(self.rc_z_1) > 0:
                    self.rc_z_2 = self.reference_cyl.get_z()
                    self.rc_speed = abs(self.rc_z_1 - self.rc_z_2)
                    self.rc_z_1 = 0

                # print(self.render.find_all_matches('**/random_prisms*')[0].get_z())
                # print(self.reference_cyl.get_z())

                return Task.again

            def update_receiver_cam(Task):
                dt = globalClock.get_dt()
                max_dist = 20
                z_offset = 20
                cam_z = self.cam.get_z()

                reference_z = self.reference_cyl.get_z()
                abs_z = abs(cam_z - reference_z)
                avg_fr = globalClock.get_average_frame_rate()
                if avg_fr == 0:
                    avg_fr = 1

                if abs_z > 30 < 60:
                    self.fall_factor *= dt
                    self.fall_factor += self.rc_speed / avg_fr
                if abs_z < 15:
                    self.fall_factor *= dt
                    self.fall_factor -= self.rc_speed / (avg_fr/2)

                falling_z = self.cam.get_z() - self.fall_factor
                self.cam.set_pos(self.x_offset, self.y_offset, falling_z)
                # self.cam.look_at(active_cylinders[0])
                base.tube_light_1.set_pos(self.cam.get_pos())

                if self.keyMap["right"]:
                    if self.x_offset <= max_dist:
                        self.x_offset += 0.1

                if self.keyMap["left"]:
                    if self.x_offset >= -max_dist:
                        self.x_offset -= 0.1

                if self.keyMap["forward"]:
                    if self.y_offset <= max_dist:
                        self.y_offset += 0.1

                if self.keyMap["backward"]:
                    if self.y_offset >= -max_dist:
                        self.y_offset -= 0.1

                if cam_z > 1690 or cam_z < reference_z:
                    text_1.set_text('Recovering level...')
                    cleanup_level()

                return Task.cont
                
            self.task_mgr.add(rotate_receiver)
            self.task_mgr.add(update_receiver_cam)
            self.task_mgr.add(measure_fall_speed)

        intro_sequence()

        def print_cam_pos_periodic(Task):
            print(self.cam.get_pos())

            Task.delay_time = 1
            return Task.again
            
        # Bullet debugger
        from panda3d.bullet import BulletDebugNode
        debugNode = BulletDebugNode('Debug')
        debugNode.show_wireframe(True)
        debugNode.show_constraints(True)
        debugNode.show_bounding_boxes(False)
        debugNode.show_normals(False)
        debugNP = self.render.attach_new_node(debugNode)
        self.world.set_debug_node(debugNP.node())

        # debug toggle function
        def toggle_debug():
            if debugNP.is_hidden():
                debugNP.show()
            else:
                debugNP.hide()

        self.accept('f1', toggle_debug)

        def update(Task):
            if self.game_start < 1:
                self.game_start = 1

            return Task.cont

        def physics_update(Task):
            dt = globalClock.get_dt()
            self.world.do_physics(dt)
            
            return Task.cont

        music_path = 'music/space_tech_pyweek37.ogg'
        self.music = self.loader.load_music(music_path)
        self.music.set_loop(True)
        self.music_time = self.music.get_time()
        self.music_paused_while_playing = False
        self.music.play()
        '''
        if self.gamepad is None:
            self.task_mgr.add(move)
            
        if int(str(devices)[0]) > 0:
            self.task_mgr.add(gp_move)
        '''
        self.task_mgr.add(update)
        # self.task_mgr.add(move_npc)
        self.task_mgr.add(physics_update)
        self.task_mgr.add(set_sun_1_task)
        self.task_mgr.add(set_sun_2_task)
        # self.task_mgr.add(print_cam_pos_periodic)

app().run()
