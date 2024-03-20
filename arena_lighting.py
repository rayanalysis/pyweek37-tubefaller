from panda3d.core import PointLight, Spotlight, AmbientLight, PerspectiveLens
from panda3d.core import LPoint3f, Point3, Vec3, Vec4, LVecBase3f, VBase4, LPoint2f


def lighting():
    # lighting entry point
    amb_light = AmbientLight('amblight')
    amb_light.set_color(Vec4(Vec3(2),1))
    amb_light_node = base.render.attachNewNode(amb_light)
    base.render.set_light(amb_light_node)

    map_light_1 = PointLight('map_light_1')
    map_light_1.set_color(Vec4(Vec3(3),1))
    map_light_1 = base.render.attach_new_node(map_light_1)
    map_light_1.set_pos(0,0,200)
    # base.render.set_light(map_light_1)

    sun_1 = Spotlight('sun_1')
    sun_1.set_shadow_caster(True, 4096, 4096)
    sun_1.set_color(Vec4(Vec3(0.7),1))
    lens = PerspectiveLens()
    lens.set_near_far(0.5, 5000)
    sun_1.set_lens(lens)
    # sun_1.set_attenuation((0.5, 0, 0.0005))
    sun_1.get_lens().set_fov(85)
    sun_1 = base.render.attach_new_node(sun_1)
    base.render.set_light(sun_1)
    sun_1.set_pos(50,0,200)
    sun_1.look_at(20,0,-1000)
    base.sun_1 = sun_1

    sun_2 = Spotlight('sun_2')
    # sun_2.set_shadow_caster(True, 512, 512)
    sun_2.set_color(Vec4(Vec3(0.3),1))
    lens = PerspectiveLens()
    lens.set_near_far(0.5, 5000)
    sun_2.set_lens(lens)
    # sun_2.set_attenuation((0.5, 0, 0.0005))
    sun_2.get_lens().set_fov(85)
    sun_2 = base.render.attach_new_node(sun_2)
    base.render.set_light(sun_2)
    sun_2.set_pos(-50,0,200)
    sun_2.look_at(-20,0,0)
    base.sun_2 = sun_2

    tube_light_1 = PointLight('tube_light_1')
    tube_light_1.set_color(Vec4(Vec3(15),1))
    tube_light_1 = base.render.attach_new_node(tube_light_1)
    tube_light_1.set_pos(0,0,0)
    # base.render.set_light(tube_light_1)
    base.tube_light_1 = tube_light_1

    # environmental reflection lighting
    base_env = loader.load_model('models/daytime_skybox.bam')
    base_env.reparent_to(base.render)
    base_env.set_scale(2)
    base_env.set_pos(0,0,0)
    base_env.set_light(map_light_1)
    # base_env.final(True)
    # base_env.set_light_off(base.render.find('**/map_light_1'))
    base.base_env = base_env

def init_flashlight():
    base.slight = Spotlight('flashlight')
    # base.slight.setShadowCaster(True, 512, 512)
    base.slight.set_color(VBase4(5.5, 5.6, 5.6, 1))  # slightly bluish
    lens = PerspectiveLens()
    lens.set_near_far(0.5, 500)
    base.slight.set_lens(lens)
    base.slight.set_attenuation((0.5, 0, 0.0005))
    base.slight.get_lens().set_fov(35)
    base.slight = base.render.attach_new_node(base.slight)
    # base.render.set_light(base.slight)
    base.slight.reparent_to(base.cam)
    base.slight.set_pos(0,0.4,0.2)

def toggle_flashlight():
    if base.render.has_light(base.slight):
        base.render.set_light_off(base.slight)
    else:
        base.render.set_light(base.slight)
