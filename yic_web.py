import web
from web import form
import yic

render = web.template.render('templates/')

urls = ('/list', 'listFiles')
app = web.application(urls, globals())

class index:
    def GET(self):
        form = myform()
        # make sure you create a copy of the form by calling it (line above)
        # Otherwise changes will appear globally
        return render.formtest(form)

    def POST(self):
        form = myform()
        if not form.validates():
            return render.formtest(form)
        else:
            # form.d.boe and form['boe'].value are equivalent ways of
            # extracting the validated arguments from the form.
            return "Grrreat success! login: %s, password: %s" % (form['login'].value, form['password'].value)

if __name__=="__main__":
    web.internalerror = web.debugerror
    app.run()

