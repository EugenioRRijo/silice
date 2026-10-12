from ui.texto_seguro import texto_seguro


def test_una_imagen_markdown_ajena_no_se_interpreta():
    nombre = "![x](http://127.0.0.1:9/robo.png) **hoja**"
    seguro = texto_seguro(nombre)
    assert "![" not in seguro and "\\!\\[x\\]" in seguro and "\\*\\*hoja\\*\\*" in seguro
