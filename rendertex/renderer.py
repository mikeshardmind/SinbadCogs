import subprocess
import threading
import re
from pathlib import Path  # NOQA:F401
import random

PDFTEX = '/usr/local/texlive/2017/bin/x86_64-linux/pdflatex'
PDFCROP = '/usr/local/texlive/2017/bin/x86_64-linux/pdfcrop'


class TexRenderer(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.tex = kwargs.pop('tex')
        self.tex = re.sub('(?<=\\\\)\n', '', self.tex)
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
            re.sub('[\W_]', '', n)
            for n in re.findall('%.{,}%\n', self.tex)
        ]
        if names:
            eqns = re.split('%.{,}%\n', self.tex)[1:]
        else:
            names = ["equation{}".format(random.randint(1, 10000))]
            eqns = [self.tex]

        for outfile, eq in zip(names, eqns):
            packages, body = [], []
            for eqline in eq.split('\n'):
                if eqline.startswith(r'\usepackage'):
                    packages.append(eqline)
                else:
                    body.append(eqline)

            with open(outfile + '.tex', 'w') as temp:
                temp.write('\documentclass[preview]{standalone}\n')
                [temp.write(pkg + '\n') for pkg in packages]
                if not any(
                    pkg.beginswith('\\usepackage{amsmath}') for pkg in packages
                ):
                    temp.write('\\usepackage{amsmath}\n')
                if not any(
                    pkg.beginswith('\\usepackage{amssymb}') for pkg in packages
                ):
                    temp.write('\\usepackage{amssymb}\n')
                if not any(line.startswith('\begin') for line in body):
                    temp.write('\\begin{document}\n')
                temp.write('\pagestyle{empty}\n')
                [temp.write(line + '\n') for line in body]
                if not any(line.startswith('\\end') for line in body):
                    temp.write('\\begin{document}\n')
                temp.write('\end{document}\n')

            subprocess.call(
                [PDFTEX, '-interaction=nonstopmode', f'{outfile}.tex']
            )

            # crop pdf, convert to png
            subprocess.call(
                [PDFCROP, f'{outfile}.pdf', f'{outfile}.pdf'],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )

            subprocess.call(
                ['convert',  '-density', f'{self.dpi}',
                 f'{outfile}.pdf',
                 '-background', 'white', '-alpha', 'remove',
                 f'{outfile}.png'],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )

            self.rendered_files.append(f'{outfile}.png')

    def cleanup(self):
        for f in self.rendered_files:
            pattern = f.replace('.png', '.*')
            for _ in Path().glob(pattern):
                _.unlink()
