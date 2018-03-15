import subprocess
import threading
import re
import pathlib
import contextlib


class TexRenderer(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.tex = kwargs.pop('tex')
        self.datapath = kwargs.pop('datapath')
        self.dpi = kwargs.pop('dpi', 300)
        self.done = threading.Event()
        self.rendered_files = []
        self.error = None
        super().__init__(*args, **kwargs)

    def run(self):
        try:
            self._render_equations()
        except Exception as e:
            self.error = str(e)
        self.done.set()

    def _render_equations(self):
        names = [
            self.datapath + re.sub('[\W_]', '', n)
            for n in re.findall('%.{,}%\n', self.tex)
        ]
        eqns = re.split('%.{,}%\n', self.tex)[1:]
        tmp_name = self.datapath + '.tempfile_latex_to_png'

        for outfile, eq in zip(names, eqns):

            packages, body = [], []
            for eqline in eq.split('\n'):
                if eqline.startswith(r'\usepackage'):
                    packages.append(eqline)
                else:
                    body.append(eqline)

            with open(tmp_name + '.tex', 'w') as temp:
                temp.write('\documentclass[preview]{standalone}\n')
                [temp.write(pkg + '\n') for pkg in packages]
                temp.write('\\begin{document}\n')
                temp.write('\pagestyle{empty}\n')
                [temp.write(line + '\n') for line in body]
                temp.write('\end{document}\n')

            subprocess.call(['pdflatex', '-interaction=nonstopmode', tmp_name])

            # crop pdf, convert to png
            subprocess.call(
                f'pdfcrop {tmp_name}.pdf {outfile}.pdf',
                shell=True)

            subprocess.call(
                f'convert -density {self.dpi} {outfile}.pdf {outfile}.png',
                shell=True
            )

            self.rendered_files.append(f'{outfile}.png')

    def cleanup(self):
        with contextlib.suppress(FileNotFoundError, OSError):
            for fname in self.rendered_files:
                pathlib.Path(fname).unlink()
                pathlib.Path(fname[:-3] + 'png').unlink()
