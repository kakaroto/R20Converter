from .translations import ogl_translations
import re

class OGLTemplate:
    @staticmethod
    def template_desc(attributes):
        return """<div class='sheet-desc sheet-info'><span>
                <span class="sheet-top"></span><span class="sheet-middle">{}</span><span class="sheet-bottom"></span>
            </span>
        </div>""".format(attributes.get("desc", ""))

    @staticmethod
    def template_traits(attributes):
        name = attributes.get("name", "")
        charname = attributes.get("charname", "")
        source = attributes.get("source", "")
        description = attributes.get("description", "")
        if source != "":
            source = """
            <div class="sheet-row sheet-subheader">
                <span class="italics">{}{}</span>
            </div>""".format(charname, source)
        if description != "":
            description = """
            <div class="sheet-row">
                <span class="desc">{}</span>
            </div>""".format(description)
        return """
        <div class="sheet-row sheet-header">
            <span>{}</span>
        </div>
        {}
        {}""".format(name, source, description)

    @staticmethod
    def render_result(attributes):
        r1 = attributes.get("r1", "")
        r2 = attributes.get("r2", "")
        global_ = attributes.get("global", "")
        always = attributes.get("always", "")
        normal = attributes.get("normal", "")
        advantage = attributes.get("advantage", "")
        disadvantage = attributes.get("disadvantage", "")
        if global_ != "":
            global_ = " + {}".format(global_)
        if always != "" or advantage != "" or disadvantage != "":
            r1_totals = re.findall(r"data-roll-total='(\d+)'", r1)
            r2_totals = re.findall(r"data-roll-total='(\d+)'", r2)
            r1_total = int(r1_totals[0]) if len(r1_totals) > 0 else 0
            r2_total = int(r2_totals[0]) if len(r2_totals) > 0 else 0
            if always != "":
                r1_class = ""
                r2_class = ""
            elif advantage != "":
                r1_class = "sheet-grey" if r1_total < r2_total else ""
                r2_class = "sheet-grey" if r1_total > r2_total else ""
            elif disadvantage != "":
                r1_class = "sheet-grey" if r1_total > r2_total else ""
                r2_class = "sheet-grey" if r1_total < r2_total else ""
            always = """
                    <div class="sheet-adv">
                        <span class='{}'>{}{}</span>
                    </div>
                    <div class="sheet-advspacer"></div>
                    <div class="sheet-adv">
                        <span class='{}'>{}{}</span>
                    </div>""".format(r1_class, r1, global_, r2_class, r2, global_)
        elif normal != "":
            normal = """
                    <div class="sheet-solo">
                        <span>{}{}</span>
                    </div>""".format(r1, global_)
        return """
            <div class="sheet-result">
                {}
                {}
            </div>""".format(always, normal)

    @staticmethod
    def render_roll_label(attributes):
        rname = attributes.get("rname", "")
        innate = attributes.get("innate", "")
        mod = attributes.get("mod", "")
        if mod != "":
            mod = "<span>({})</span>".format(mod)
        if innate != "":
            innate = """<span class="sheet-grey">{}{}</span>""".format(", " if rname != "" else "", innate)
        # TODO: Add use case of roll being a crit, show rnamec for example
        return """
            <div class="sheet-label">
                <span>{}{}{}</span>
            </div>""".format(rname, innate, mod)

    @staticmethod
    def render_save(attributes, attack):
        save = attributes.get("save", "")
        if save != "":
            savedesc = attributes.get("savedesc", "")
            if savedesc != "":
                savedesc = """
                    <div class="sheet-sublabel">
                        <span>{}</span>
                    </div>""".format(savedesc)
            save = """
                <div class="sheet-{} sheet-save">
                <div class="sheet-savedc">
                    <span class="sheet-rolltemplate-inline">DC</span><span class="sheet-rolltemplate-inline">{}</span>
                </div>
                {}
                <div class="label">
                    <span class="sheet-rolltemplate-inline">{}</span> <span class="sheet-rolltemplate-inline">Save</span>
                </div>
            </div>""".format("desc" if attack != "" else "atk", attributes.get("savedc", ""), savedesc, attributes.get("saveattr", ""))
        return save

    @staticmethod
    def render_charname(attributes):
        charname = attributes.get("charname", "")
        if charname != "":
            return """<div class="sheet-charname">
                    <span>{}</span>
                </div>""".format(charname)
        return ""

        
    @staticmethod
    def render_range(attributes):
        range_ = attributes.get("range", "")
        if range_ != "":
            return """
                <div class="sheet-sublabel">
                    <span>{}</span>
                </div>""".format(range_)
        return ""

    @staticmethod
    def render_globaldamage(attributes):
        globaldamage = attributes.get("globaldamage", "")
        globaldamagetype = attributes.get("globaldamagetype", "")
        totals = re.findall(r"data-roll-total='(\d+)'", globaldamage)
        total = int(totals[0]) if len(totals) > 0 else 0
        # TODO: add globaldamagecrit
        if total != 0:
            return """
                <div class="sheet-desc">
                    <span>{}</span>
                    <span class="sheet-sublabel">{}</span>
                </div>""".format(total, globaldamagetype)
        return ""

    @staticmethod
    def render_hldmg(attributes):
        hldmg = attributes.get("hldmg", "")
        hldmgtype = attributes.get("dmg1type", "")
        totals = re.findall(r"data-roll-total='(\d+)'", hldmg)
        total = int(totals[0]) if len(totals) > 0 else 0
        # TODO: add hldmgcrit
        if total != 0:
            return """
                <div class="sheet-desc">
                    <span>{}</span>
                    <span class="sheet-sublabel">{}</span>
                    <div class="sheet-label">
                        <span>Higher Level Cast</span>
                    </div>
                </div>""".format(total, hldmgtype)
        return ""


    @staticmethod
    def render_dmg(attributes, crit):
        dmg1 = attributes.get("dmg1", "")
        dmg1flag = attributes.get("dmg1flag", "")
        dmg1type = attributes.get("dmg1type", "")
        dmg2 = attributes.get("dmg2", "")
        dmg2flag = attributes.get("dmg2flag", "")
        dmg2type = attributes.get("dmg2type", "")
        crit1 = attributes.get("crit1", "")
        crit2 = attributes.get("crit2", "")

        if crit != "":
            crit1 = " + {}".format(crit1)
            crit2 = " + {}".format(crit2)
        else:
            crit1 = crit2 = ""
        if dmg1flag != "" and dmg2flag == "":
            dmg = """<div class="sheet-solo">
                            <span class="sheet-damage">{}{}</span>
                            <span class="sheet-sublabel">{}</span>
                        </div>""".format(dmg1, crit1, dmg1type)
        elif dmg1flag == "" and dmg2flag != "":
            dmg = """<div class="sheet-solo">
                            <span class="sheet-damage">{}{}</span>
                            <span class="sheet-sublabel">{}</span>
                        </div>""".format(dmg2, crit2, dmg2type)
        elif dmg1flag != "" and dmg2flag != "":
            dmg = """
                        <div class="sheet-adv">
                            <span class="sheet-damage">{}{}</span>
                            <span class="sheet-sublabel">{}</span>
                        </div>
                        <div class="sheet-advspacer"></div>
                        <div class="sheet-adv">
                            <span class="sheet-damage">{}{}</span>
                            <span class="sheet-sublabel">{}</span>
                        </div>""".format(dmg1, crit1, dmg1type, dmg2, crit2, dmg2type)
        else:
            dmg = ""
        return dmg

    @classmethod
    def template_simple(klass, attributes):
        return """<div class="sheet-container">
        {}
        {}
        {}
        </div>""".format(klass.render_result(attributes), klass.render_roll_label(attributes), klass.render_charname(attributes))

    @classmethod
    def template_atk(klass, attributes):
        desc = attributes.get("desc", "")
        if desc != "":
            desc = klass.template_desc(attributes)
        return """<div class="sheet-container">
        {}
        {}
        {}
        {}
        {}</div>""".format(klass.render_result(attributes), klass.render_range(attributes),
                           klass.render_roll_label(attributes), klass.render_charname(attributes), desc)

    @classmethod
    def template_dmg(klass, attributes):
        attack = attributes.get("attack", "")
        crit = attributes.get("crit", "")
        if attack == "":
            desc = attributes.get("desc", "")
            range_ = klass.render_range(attributes)
            charname = klass.render_charname(attributes)
            label = klass.render_roll_label(attributes)
            if desc != "":
                desc = klass.template_desc(attributes)
        else:
            range_ = ""
            charname = ""
            label = ""
            desc = ""
        save = klass.render_save(attributes, attack)
        dmg = klass.render_dmg(attributes, crit)
        globaldamage = klass.render_globaldamage(attributes)
        hldmg = klass.render_hldmg(attributes)
        return """
        {}
        {}
        {}
        {}
        <div class="sheet-container sheet-damagetemplate">
            <div class="sheet-result">
            {}
            </div>
            {}
            {}
            {}
        </div>""".format(save, desc, globaldamage, hldmg, dmg, range_, label, charname)

    @classmethod
    def template_atkdmg(klass, attributes):
        attack = attributes.get("attack", "")
        damage = attributes.get("damage", "")
        crit = attributes.get("crit", "")
        desc = attributes.get("desc", "")
        if desc != "":
            desc = klass.template_desc(attributes)
        if attack != "":
            attack = """<div class="sheet-container sheet-atk">{}{}{}{}</div>""" \
                .format(klass.render_result(attributes), klass.render_range(attributes), 
                        klass.render_roll_label(attributes), klass.render_charname(attributes))
        if damage != "":
            dmg_footer = ""
            if attack == "":
                dmg_footer = "{}{}{}".format(klass.render_range(attributes),
                                             klass.render_roll_label(attributes),
                                             klass.render_charname(attributes))
            damage = """
                <div class="sheet-container sheet-damagetemplate">
                    <div class="sheet-result">
                    {}
                    </div>
                    {}
                </div>""".format(klass.render_dmg(attributes, crit), dmg_footer)

        return """{}
                {}
                {}
                {}""".format(attack, klass.render_save(attributes, attack), desc, damage)

    @classmethod
    def template_spell(klass, attributes):
        name = attributes.get("name", "")
        innate = attributes.get("innate", "")
        level = attributes.get("level", "")
        ritual = attributes.get("ritual", "")
        castingtime = attributes.get("castingtime", "")
        range_ = attributes.get("range", "")
        target = attributes.get("target", "")
        v = attributes.get("v", "")
        s = attributes.get("s", "")
        m = attributes.get("m", "")
        material = attributes.get("material", "")
        duration = attributes.get("duration", "")
        description = attributes.get("description", "")
        concentration = attributes.get("concentration", "")
        athigherlevels = attributes.get("athigherlevels", "")
        if innate != "":
            innate = """<span class="sheet-grey">{}{}</span>""".format(", " if name != "" else "", innate)
        if ritual != "":
            ritual = "(<span>Ritual</span>)"
        if castingtime != "":
            castingtime = """
            <div class="sheet-row">
                <span class="sheet-bold">Casting Time:</span> <span>{}</span>
            </div>""".format(castingtime)
        if range_ != "":
            range_ = """
            <div class="sheet-row">
                <span class="sheet-bold">Range:</span> <span>{}</span>
            </div>""".format(range_)
        if target != "":
            target = """
            <div class="sheet-row">
                <span class="sheet-bold">Target:</span> <span>{}</span>
            </div>""".format(target)
        components = ""
        if v != "":
            components += "V"
        if s != "":
            components += (", " if components != "" else "") + "S"
        if m != "":
            components += (", " if components != "" else "") + "M"
            if material != "":
                components += " ({})".format(material)
        if duration != "":
            concentration = attributes.get("concentration", "")
            duration = """
            <div class="sheet-row">
                <span class="sheet-bold">Duration:</span> <span>{}{}</span>
            </div>""".format("<span>Concentration</span>" if concentration != "" else "", duration)
        if description != "":
            description = """
            <div class="sheet-row">
                <span class="sheet-description">{}</span>
            </div>""".format(description)
        if athigherlevels != "":
            athigherlevels = """
            <div class="sheet-row">
                <span class="sheet-bold sheet-italics">At Higher Levels</span>. <span class="sheet-description">{}</span>
            </div>""".format(athigherlevels)
        return """
        <div class="sheet-container">
            <div class="sheet-title sheet-row">
                <span>{}</span>{}
            </div>
            <div class="sheet-italics sheet-row">
                <span>{}{}</span>
            </div>
            <div class="sheet-spacer"></div>
            {}
            {}
            {}
            <div class="sheet-row">
                <span class="sheet-bold">Components:</span>
                <span>{}</span>
            </div>
            {}
            <div class="sheet-spacer"></div>
            {}
            {}
        </div>
        """.format(name, innate, level, ritual, castingtime, range_, target, components, duration, description, athigherlevels)

    @staticmethod
    def render_npc(attributes, type_):
        rname = attributes.get("rname", "")
        name = attributes.get("name", "")
        r1 = attributes.get("r1", "")
        r2 = attributes.get("r2", "")
        always = attributes.get("always", "")
        normal = attributes.get("normal", "")
        advantage = attributes.get("advantage", "")
        disadvantage = attributes.get("disadvantage", "")
        if name != "":
            name = """
            <div class="sheet-row sheet-subheader">
                <span class="sheet-italics">{}</span>
            </div>""".format(name)
        if always != "" or advantage != "" or disadvantage != "":
            r1_totals = re.findall(r"data-roll-total='(\d+)'", r1)
            r2_totals = re.findall(r"data-roll-total='(\d+)'", r2)
            r1_total = int(r1_totals[0]) if len(r1_totals) > 0 else 0
            r2_total = int(r2_totals[0]) if len(r2_totals) > 0 else 0
            if always != "":
                r1_class = ""
                r2_class = ""
            elif advantage != "":
                r1_class = "sheet-grey" if r1_total < r2_total else ""
                r2_class = "sheet-grey" if r1_total > r2_total else ""
            elif disadvantage != "":
                r1_class = "sheet-grey" if r1_total > r2_total else ""
                r2_class = "sheet-grey" if r1_total < r2_total else ""
            roll = """<span class="sheet-italics">{}: </span><span class="{}">{}</span><span> | </span><span class="{}">{}</span>""" \
                .format(type_, r1_class, r1, r2_class, r2)
        elif normal != "":
            roll = """<span class="sheet-italics">{}: </span><span>{}</span>""".format(type_, r1)
        return """
        <div class="sheet-row sheet-header">
            <span>{}</span>
        </div>
        {}
        <div class="sheet-arrow-right"></div>
        <div class="sheet-row">
        {}
        </div>
        """.format(rname, name, roll)
        
    @staticmethod
    def render_npcdmg(attributes, crit):
        dmg1flag = attributes.get("dmg1flag", "")
        dmg1type = attributes.get("dmg1type", "")
        dmg1 = attributes.get("dmg1", "")
        crit1 = attributes.get("crit1", "")
        dmg2flag = attributes.get("dmg2flag", "")
        dmg2type = attributes.get("dmg2type", "")
        dmg2 = attributes.get("dmg2", "")
        crit2 = attributes.get("crit2", "")
        if dmg1flag != "":
            damage1 = "{}{}{}".format(dmg1, (" + " + crit1) if crit != "" else "", dmg1type)
        else:
            damage1 = ""
        if dmg2flag != "":
            damage2 = "{}{}{}".format(dmg2, (" + " + crit2) if crit != "" else "", dmg2type)
        else:
            damage2 = ""
        return """
        <div class="sheet-container sheet-dmgcontainer sheet-damagetemplate">
            <span class="sheet-italics">Damage: </span>
            <span>
            {}
            {}
            {}
            </span>
        </div>
        """.format(damage1, " + " if damage1 != "" and damage2 != "" else "", damage2)

    @classmethod
    def template_npc(klass, attributes):
        type_ = attributes.get("type", "")
        return klass.render_npc(attributes, type_)

    @classmethod
    def template_npcatk(klass, attributes):
        type_ = attributes.get("type", "")
        description = attributes.get("description", "")
        if description != "":
            description = """
            <div class="sheet-row">
                <span class="sheet-desc">{}</span>
            </div>""".format(description)
        #TODO: rnamec handling for critical
        return """{}
        {}
        """.format(klass.render_npc(attributes, type_), description)
    @classmethod
    def template_npdmg(klass, attributes):
        crit = attributes.get("crit", "")
        return klass.render_npcdmg(attributes, crit)

    @classmethod
    def template_npaction(klass, attributes):
        crit = attributes.get("crit", "")
        description = attributes.get("description", "")
        if description != "":
            description = """
            <div class="sheet-row">
                <span class="sheet-desc">{}</span>
            </div>""".format(description)
        return """
        {}
        {}
        {}
        """.format(klass.render_npc(attributes, "Attack"), description, klass.render_npcdmg(attributes, crit))

    @classmethod
    def template_mancerroll(klass, attributes):
        title = attributes.get("title", "")
        c1 = attributes.get("c1", "")
        option = ""
        if c1 != "":
            totals = re.findall(r"data-roll-total='(\d+)'", c1)
            total = int(totals[0]) if len(totals) > 0 else 0
            c1 = "<span>{}</span>".format(c1)
            option = attributes.get("option{}".format(total), "")

        rolls = ""
        for i in range(6):
            r = attributes.get("r{}".format(i + 1), "")
            if r != "":
                rolls += """
                <div class="sheet-row">
                    <span class="sheet-desc">Roll {}: </span>
                    <span class="sheet-result">{}</span>
                </div>""".format(i + 1, r)
        return """
        <div class="sheet-container">
            <div class="sheet-row sheet-header">
                <span>
                    {}
                    {}
                </span>
            </div>
            {}
            <div class="sheet-row">
                <span class="sheet-desc">
                {}
                </span>
            </div>
        </div>
            """.format(title, c1, rolls, option)

            
    @classmethod
    def template_mancerhproll(klass, attributes):
        title = attributes.get("title", "")
        c1 = attributes.get("c1", "")
        a1 = attributes.get("a1", "")
        if c1 != "":
            c1 = "<span>{}</span>".format(c1)

        if a1 != "":
            a1 = """
                <div class="sheet-row">
                    <span class="sheet-desc">Average: </span>
                    <span class="sheet-result">{}</span>
                </div>""".format(a1)
        rolls = ""
        for i in range(20):
            r = attributes.get("r{}".format(i + 1), "")
            if r != "":
                rolls += """
                <div class="sheet-row">
                    <span class="sheet-desc">Roll {}: </span>
                    <span class="sheet-result">{}</span>
                </div>""".format(i + 1, r)
        return """
        <div class="sheet-container">
            <div class="sheet-row sheet-header">
                <span>
                    {}
                    {}
                </span>
            </div>
            {}
            {}
        </div>
            """.format(title, c1, a1, rolls)