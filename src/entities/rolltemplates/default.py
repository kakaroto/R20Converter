
class DefaultTemplate:
    @staticmethod
    def _capitalizeAll(sentence):
        return " ".join(map(lambda x: x.capitalize(), sentence.split(" ")))

    @staticmethod
    def template_default(attributes):
        trs = ""
        for attr in attributes.keys():
            if attr == "name":
                continue
            trs += "<tr><td>{}</td><td>{}</td>".format(DefaultTemplate._capitalizeAll(attr), attributes[attr])
        return """<table>
                    <caption>{}</caption>
                    <tbody>{}</tbody>
                  </table>""".format(attributes.get("name", ""), trs)
