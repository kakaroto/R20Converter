import re
from .translations import ogl_translations, shaped_translations
from .ogl import OGLTemplate
from .default import DefaultTemplate
from .shaped import ShapedTemplate

RollTemplates = [DefaultTemplate, OGLTemplate, ShapedTemplate]

class RollTemplate:
    def __init__(self, template, content, rolls):
        self.attributes = {}
        self.template = template
        self.content = content
        self.rolls = rolls
        # Check for "{{key=value}}" or "key=value"
        args = re.findall(r'(?:{{([^=]+)=(.*?)}}(?= |{|$))|(?:(?:\s|^)(?<!{{)([\w\s]+)=(.*?)(?=(?:\s+{{)|(?:\s+\w+=)|(?:\s*$)))', content, re.DOTALL)
        for arg in args:
            if arg[0] == "" and arg[2] == "":
                continue
            if arg[0] != "":
                (key, value) = arg[0:2]
            else:
                (key, value) = arg[2:4]
            value = re.sub(r"\^{([^}]+)}", self._translateTemplateString, value)
            self.attributes[key] = re.sub(r'\$\[\[(\d+)\]\]', self._replaceInlineRolls, value)

    def _translateTemplateString(self, match):
        ogl = ogl_translations.get(match.group(1), None)
        if ogl is not None:
            return ogl
        return shaped_translations.get(match.group(1), match.group(0))

    def _replaceInlineRolls(self, match):
        idx = int(match.group(1))
        if idx < 0 or idx >= len(self.rolls):
            return match.group(0)
        return self.rolls[idx].getInline()

    def toHTML(self):
        template_renderer = None
        for renderer in RollTemplates:
            template_renderer = getattr(renderer, "template_%s" % self.template.replace("-", "_"), None)
            if template_renderer is not None:
                break
        if template_renderer is None:
            template_renderer = DefaultTemplate.template_default
        template_name = template_renderer.__name__[9:]
        return '<div class="roll20-rolltemplate roll20-original-template-{} sheet-rolltemplate-{}">{}</div>'.format(self.template, template_name, template_renderer(self.attributes))
