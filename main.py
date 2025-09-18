import maya.cmds as cmds
import math

def jntRig(object='', side='l', part='arm', primary_axis='X'):

    jntList = cmds.listRelatives(object, allDescendents=True)

    if jntList == None:
        jntList = cmds.ls(object)
    else:
        jntList.append(object)
        jntList.reverse()

    base_name = side + '_' + part

    if part == 'arm':
        alias_list=['clav', 'arm', 'elbow', 'wrist']
        ik_chain = create_chain(side, jntList[1:], alias_list[1:], 'IK')
        fk_chain = create_chain(side, jntList[1:], alias_list[1:], 'FK')
        anim_chain = create_chain(side, jntList, alias_list, 'anim')

        twist_list = []
        for j in range(1, len(anim_chain)-1):
             twist_list.append(addTwistJnts(anim_chain[j], 5))

        print(twist_list)

        #create FK_IK-Anchor
        fkik_joint = cmds.joint(anim_chain[0], name= side + '_' + alias_list[0] + '_FKIK_jnt')
        cmds.parent(world=True)
        cmds.parent(ik_chain[0], fkik_joint)
        cmds.parent(fk_chain[0], fkik_joint)
        cmds.parentConstraint(anim_chain[0], fkik_joint)

    elif part == 'leg':
        alias_list=['leg', 'knee', 'foot', 'toe']
        ik_chain = create_chain(side, jntList, alias_list, 'IK')
        fk_chain = create_chain(side, jntList, alias_list, 'FK')
        anim_chain = create_chain(side, jntList, alias_list, 'anim')
        twist_list = []
        for j in range(0, len(anim_chain)-2):
             twist_list.append(addTwistJnts(anim_chain[j], 5))

        print(twist_list)

    if part == 'arm':
        FKIK_switch = fkik_blend(side, part, ik_chain, fk_chain, anim_chain[1:])
    else:
        FKIK_switch = fkik_blend(side, part, ik_chain, fk_chain, anim_chain)

    #Create FK-ctrls
    fk_ctrls=[]
    for i, alias in enumerate(fk_chain):
        ctrl = cmds.circle(radius=8, normal=(1,0,0), name= alias.replace('jnt', 'ctl'))
        zro = cmds.group(ctrl, name=alias.replace('jnt', 'zro'))
        if i != 0:
            cmds.parent(zro, par[0])
        cmds.matchTransform(zro, fk_chain[i])
        par = ctrl
        cmds.pointConstraint(ctrl,fk_chain[i])
        cmds.connectAttr(ctrl[0] + '.rotate', fk_chain[i] + '.rotate')
        fk_ctrls.append(zro)

    #Create stretch-function
    if part == 'arm':
        ik_sys = create_ik(side, alias_list[1:], ik_chain)
        add_ik_stretch(side, part, ik_chain, ik_sys['ik_ctrl'], ik_sys['pv_ctrl'], primary_axis, twist_list)
    elif part == 'leg':
        ik_sys = create_ik(side, alias_list[:-1], ik_chain[:-1])
        add_ik_stretch(side, part, ik_chain[:-1], ik_sys['ik_ctrl'], ik_sys['pv_ctrl'], primary_axis, twist_list)

    #set visibility
    FKIK_rev = cmds.createNode('reverse', name= base_name + '_FKIK_rev')
    cmds.connectAttr(FKIK_switch[0] + '.FKIK', ik_sys['ik_zro'] + '.visibility')
    cmds.connectAttr(FKIK_switch[0] + '.FKIK', ik_sys['pv_zro'] + '.visibility')
    cmds.connectAttr(FKIK_switch[0] + '.FKIK', FKIK_rev + '.input.inputX')
    cmds.connectAttr(FKIK_rev + '.output.outputX', fk_ctrls[0] + '.visibility')


def addTwistJnts(start, jntNum):
    # create Twist_Jnts
    twist_jnt = []
    for i in range(jntNum):
        jnt = cmds.joint(name= start.replace('anim', 'twist') + '_' + str(i))
        cmds.parent(jnt, start)
        for attr in ('translate', 'rotate'):
            for axis in ('X', 'Y', 'Z'):
                cmds.setAttr(jnt + '.' + attr + '.' + attr + axis, 0)
        twist_jnt.append(jnt)

    return twist_jnt

def create_chain(side, joint_list, alias_list, suffix='IK'):
    chain_list = []
    for j, a in zip(joint_list, alias_list):
        if j == joint_list[0]:
            par = None
        else:
            par = jnt
        jnt = cmds.joint(par, name='{}_{}_{}_jnt'.format(side, a, suffix))
        cmds.delete(cmds.pointConstraint(j, jnt, maintainOffset=False))
        cmds.delete(cmds.orientConstraint(j, jnt, maintainOffset=False))
        cmds.makeIdentity(jnt, apply=1, translate=0, rotate=1, scale=0)
        chain_list.append(jnt)
    #    cmds.joint(chain_list[:1], e=True, zeroScaleOrient=True, orientJoint='xyz', secondaryAxisOrient='yup')
    for axis in ['X', 'Y', 'Z']:
        cmds.setAttr(chain_list[-1] + '.jointOrient' + axis, 0)

    return chain_list


def fkik_blend(side, part, ik_list, fk_list, anim_list):
    #create Locator-switch for FKIK
    FKIK_switch = cmds.spaceLocator(name= side + '_' + part + '_FKIK_switch')
    cmds.matchTransform(FKIK_switch, anim_list[-1])
    dist = 10
    if side == 'r':
        cmds.move(-dist,0, relative=True)
    else:
        cmds.move(dist,0, relative=True)
    loc_shape = cmds.listRelatives(FKIK_switch, shapes=True)
    cmds.addAttr(loc_shape, longName='FKIK', attributeType='float', defaultValue=0.0, minValue=0.0, maxValue=1.0, keyable=True, hidden=False)

    for fk, ik, anim in zip(fk_list, ik_list, anim_list):
        blnd_node = cmds.createNode('pairBlend', name= anim.replace('anim_jnt', 'FKIK_blnd'))
        cmds.connectAttr(loc_shape[0] + '.FKIK', blnd_node + '.weight')
        for attr in ['translate', 'rotate']:
            cmds.connectAttr(fk + '.' + attr, blnd_node + '.in' + str.capitalize(attr) + str(1))
            cmds.connectAttr(ik + '.' + attr, blnd_node + '.in' + str.capitalize(attr) + str(2))
            cmds.connectAttr(blnd_node + '.out' + str.capitalize(attr), anim + '.' + attr)

    return loc_shape


def create_ik(side, alias_list, ik_chain):
    #Create IK-ctrls
    ik_ctrl = cmds.circle(sections=4, degree=1, radius=8, normal=(1, 0 ,0 ), name='{}_{}_IK_ctl'.format(side,alias_list[-1]))
    ik_zro = cmds.group(ik_ctrl, name='{}_{}_IK_zro'.format(side, alias_list[-1]))
    cmds.orientConstraint(ik_ctrl, ik_chain[-1], maintainOffset=True)
    cmds.matchTransform(ik_zro, ik_chain[-1], position=True, rotation=False)
    #PV-Ctrl
    pv_ctrl = cmds.circle(sections=4, degree=1, radius=8, normal=(0, 0 ,1), name='{}_{}_PV_ctl'.format(side,alias_list[1]))
    pv_zro = cmds.group(pv_ctrl, name='{}_{}_PV_zro'.format(side, alias_list[1]))
    cmds.pointConstraint(ik_chain[-1], pv_zro, maintainOffset=False)
    cmds.delete(pv_zro, constraints=True)
    #cmds.delete(cmds.aimConstraint(ik_chain[1], pv_zro, wut='Vector', aim=(1,0,0), wu=(0,1,0)))
    cmds.delete(pv_zro, constraints=True)
    cmds.move(0,0,10, pv_zro, objectSpace=True, worldSpaceDistance=True, relative=True)

    ikH, ikH_effector = cmds.ikHandle(startJoint=ik_chain[0], endEffector=ik_chain[-1], name='{}_{}_ikH'.format(side, alias_list[0]))
    cmds.poleVectorConstraint(pv_ctrl, ikH)
    cmds.parent(ikH, ik_ctrl[0])

    ik_dict = {'ik_ctrl': ik_ctrl,
               'ik_zro': ik_zro,
               'pv_ctrl': pv_ctrl,
               'pv_zro': pv_zro
               }

    return ik_dict


def add_ik_stretch(side, part, ik_chain, wrist_ctl, pv_ctl, primary_axis, twist_list):

    base_name = side + '_' + part

    limb_dist = cmds.createNode('distanceBetween', name=base_name + '_DST')
    limb_cnd = cmds.createNode('condition', name=base_name + '_CND')
    start_loc = cmds.spaceLocator(name= base_name + '_START_LOC')[0]
    end_loc = cmds.spaceLocator(name= base_name + '_END_LOC')[0]
    stretch_mdv = cmds.createNode('multiplyDivide', name=base_name + '_stretch_MDV')

    length_a = distance_between(ik_chain[0], ik_chain[1])
    length_b = distance_between(ik_chain[1], ik_chain[2])
    length_total = length_a + length_b

    # measure limb length
    cmds.pointConstraint(ik_chain[0], start_loc, maintainOffset=False)
    cmds.pointConstraint(wrist_ctl, end_loc, maintainOffset=False)
    cmds.connectAttr(start_loc + '.worldMatrix[0]', limb_dist + '.inMatrix1')
    cmds.connectAttr(end_loc + '.worldMatrix[0]', limb_dist + '.inMatrix2')


    # calculate length ratio
    cmds.connectAttr(limb_dist + '.distance', stretch_mdv + '.input1X')
    cmds.setAttr(stretch_mdv + '.input2X', length_total)
    cmds.setAttr(stretch_mdv +'.operation', 2)

    cmds.connectAttr(stretch_mdv + '.outputX', limb_cnd + '.firstTerm')
    cmds.connectAttr(stretch_mdv + '.outputX', limb_cnd + '.colorIfTrueR')
    cmds.setAttr(limb_cnd + '.secondTerm', 1)
    cmds.setAttr(limb_cnd + '.operation', 3)

    # add on/off switch for stretch
    cmds.addAttr(wrist_ctl, attributeType='double', min=0, max=1, defaultValue=1, keyable=True, longName='doStretch' )
    doStretch_bta = cmds.createNode('blendTwoAttr',
                                  name=base_name + '_doStretch_BTA')
    cmds.setAttr(doStretch_bta + '.input[0]', 1)
    cmds.connectAttr(limb_cnd + '.outColorR', doStretch_bta + '.input[1]')
    cmds.connectAttr(wrist_ctl[0] + '.doStretch', doStretch_bta + '.attributesBlender')

    #calculate stretch
    streched_Mdv = cmds.createNode('multiplyDivide', name= base_name + '_strechedValue_MDV')
    cmds.setAttr(streched_Mdv + '.operation', 1)
    cmds.connectAttr(doStretch_bta + '.output', streched_Mdv + '.input1X')
    cmds.connectAttr(doStretch_bta + '.output', streched_Mdv + '.input1Y')
    cmds.setAttr(streched_Mdv + '.input2X', length_a)
    cmds.setAttr(streched_Mdv + '.input2Y', length_b)

    #Pin-System
    cmds.addAttr(wrist_ctl, attributeType='double', min=0, max=1, defaultValue=0, keyable=True, longName='Pin' )
    toPV = cmds.createNode('distanceBetween', name=base_name + '_toPV')
    fromPV = cmds.createNode('distanceBetween', name=base_name + '_fromPV')
    cmds.connectAttr(start_loc + '.worldMatrix[0]', toPV + '.inMatrix1')
    cmds.connectAttr(pv_ctl[0] + '.worldMatrix[0]', toPV + '.inMatrix2')
    cmds.connectAttr(pv_ctl[0] + '.worldMatrix[0]', fromPV + '.inMatrix1')
    cmds.connectAttr(end_loc + '.worldMatrix[0]', fromPV + '.inMatrix2')

    upPin = cmds.createNode('blendTwoAttr', name=base_name + '_upPin_BTA')
    loPin = cmds.createNode('blendTwoAttr', name=base_name + '_loPin_BTA')
    cmds.connectAttr(streched_Mdv + '.outputX', upPin + '.input[0]')
    cmds.connectAttr(toPV + '.distance', upPin + '.input[1]')
    cmds.connectAttr(streched_Mdv + '.outputY', loPin + '.input[0]')
    cmds.connectAttr(fromPV + '.distance', loPin + '.input[1]')
    cmds.connectAttr(wrist_ctl[0] + '.Pin', upPin + '.attributesBlender')
    cmds.connectAttr(wrist_ctl[0] + '.Pin', loPin + '.attributesBlender')

    #create Nudge
    cmds.addAttr(wrist_ctl, attributeType='double', defaultValue=0, keyable=True, longName='Nudge')
    nudge_mdl =cmds.createNode('multDoubleLinear', name= base_name + '_nudge_MDL')
    cmds.connectAttr(wrist_ctl[0] + '.Pin', nudge_mdl + '.input1')
    cmds.setAttr(nudge_mdl + '.input2', 0.001)

    nudge_pma = cmds.createNode('plusMinusAverage', name=base_name + '_nudge_PMA')
    cmds.connectAttr(upPin + '.output', nudge_pma + '.input2D[0].input2Dx')
    cmds.connectAttr(loPin + '.output', nudge_pma + '.input2D[0].input2Dy')
    cmds.connectAttr(nudge_mdl + '.output', nudge_pma + '.input2D[1].input2Dx')
    cmds.connectAttr(nudge_mdl + '.output', nudge_pma + '.input2D[1].input2Dy')

    if side == 'r':
        inv_node = cmds.createNode('multiplyDivide', name= base_name + '_INV')
        cmds.connectAttr(nudge_pma + '.output2D.output2Dx', inv_node + '.input1.input1X')
        cmds.connectAttr(nudge_pma + '.output2D.output2Dy', inv_node + '.input1.input1Y')
        cmds.setAttr(inv_node + '.input2.input2X', -1)
        cmds.setAttr(inv_node + '.input2.input2Y', -1)
        cmds.connectAttr(inv_node + '.output.outputX', ik_chain[1] + '.translate' + primary_axis)
        cmds.connectAttr(inv_node + '.output.outputY', ik_chain[2] + '.translate' + primary_axis)

        connector = ('x', 'y')
        for j, end in enumerate(connector):
            r = 0
            twistMdv1 = cmds.createNode('multiplyDivide', name=base_name + '_twist_MDV'+ str(j))
            XYZ =('X', 'Y', 'Z')
            for i, axis in enumerate(XYZ):
                cmds.connectAttr(inv_node + '.output.output' + end.upper(), twistMdv1 + '.input1.input1'+ axis[0])
                cmds.setAttr(twistMdv1 + '.input2.input2'+ axis[0], r)
                r += 0.25
                cmds.connectAttr(twistMdv1 + '.output.output'+ axis[0], twist_list[j][i] + '.translate.translateX')
            cmds.setAttr(twistMdv1 + '.input2.input2X', 0.05)

            twistMdv2 = cmds.createNode('multiplyDivide', name=base_name + '_twist_MDV'+ str(j+1))
            XY =('X', 'Y')
            for i, axis in enumerate(XY):
                cmds.connectAttr(inv_node + '.output.output' + end.upper(), twistMdv2 + '.input1.input1'+ axis[0])
                cmds.setAttr(twistMdv2 + '.input2.input2'+ axis[0], r)
                r += 0.25
                cmds.connectAttr(twistMdv2 + '.output.output'+ axis[0], twist_list[j][i+3] + '.translate.translateX')
            cmds.setAttr(twistMdv2 + '.input2.input2Y', 0.95)


    else:
        cmds.connectAttr(nudge_pma + '.output2D.output2Dx', ik_chain[1] + '.translate' + primary_axis)
        cmds.connectAttr(nudge_pma + '.output2D.output2Dy', ik_chain[2] + '.translate' + primary_axis)

        connector = ('x', 'y')
        for j, end in enumerate(connector):
            r = 0
            twistMdv1 = cmds.createNode('multiplyDivide', name=base_name + '_twist_MDV'+ str(j))
            XYZ =('X', 'Y', 'Z')
            for i, axis in enumerate(XYZ):
                cmds.connectAttr(nudge_pma + '.output2D.output2D'+ end, twistMdv1 + '.input1.input1'+ axis[0])
                cmds.setAttr(twistMdv1 + '.input2.input2'+ axis[0], r)
                r += 0.25
                cmds.connectAttr(twistMdv1 + '.output.output'+ axis[0], twist_list[j][i] + '.translate.translateX')
            cmds.setAttr(twistMdv1 + '.input2.input2X', 0.05)

            twistMdv2 = cmds.createNode('multiplyDivide', name=base_name + '_twist_MDV'+ str(j+1))
            XY =('X', 'Y')
            for i, axis in enumerate(XY):
                cmds.connectAttr(nudge_pma + '.output2D.output2D' + end, twistMdv2 + '.input1.input1'+ axis[0])
                cmds.setAttr(twistMdv2 + '.input2.input2'+ axis[0], r)
                r += 0.25
                cmds.connectAttr(twistMdv2 + '.output.output'+ axis[0], twist_list[j][i+3] + '.translate.translateX')
            cmds.setAttr(twistMdv2 + '.input2.input2Y', 0.95)



    # return dictionary to pass arguments into other function
    return_dict = {'measure_locs': [start_loc, end_loc],
                   'length_total': length_total,
                   'mdn': stretch_mdv,
                   'cnd': limb_cnd
                   }
    return return_dict



def distance_between(node_a, node_b):
    point_a = cmds.xform(node_a, query=True, worldSpace=True, rotatePivot=True)
    point_b = cmds.xform(node_b, query=True, worldSpace=True, rotatePivot=True)

    dist = math.sqrt(sum([pow((b - a), 2) for b, a in zip(point_b, point_a)]))
    return dist


jntRig('l_clav', 'l', 'arm')
jntRig('r_clav', 'r', 'arm')
jntRig('l_leg', 'l', 'leg')
jntRig('r_leg', 'r', 'leg')