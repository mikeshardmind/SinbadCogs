import subprocess
import threading
import re
from pathlib import Path
import random

PDFTEX = '/usr/local/texlive/2017/bin/x86_64-linux/pdflatex'
PDFCROP = '/usr/local/texlive/2017/bin/x86_64-linux/pdfcrop'


class TexRenderer(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.tex = kwargs.pop('tex')
        self.tex = re.sub('(?<=\\\\)\n', '', self.tex)
        self.dpi = kwargs.pop('dpi', 300)
        self.cwd = kwargs.pop('cwd', Path('.'))
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

        for name, eq in zip(names, eqns):
            packages, body = [], []
            for eqline in eq.split('\n'):
                if eqline.startswith(r'\usepackage'):
                    packages.append(eqline)
                else:
                    body.append(eqline)

            tempfile = self.cwd / f'{name}.tex'

            with tempfile.open(mode='w') as temp:
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

            subprocess.run(
                [PDFTEX, '-interaction=nonstopmode', f'{name}.tex'],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                cwd=self.cwd
            )

            subprocess.run(
                [PDFCROP, f'{name}.pdf', f'{name}.pdf'],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                cwd=self.cwd
            )

            subprocess.run(
                ['convert',  '-density', f'{self.dpi}',
                 f'{name}.pdf',
                 '-background', 'white', '-alpha', 'remove',
                 f'{name}.png'],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                cwd=self.cwd
            )

            xpath = self.cwd / f'{name}.png'
            self.rendered_files.append(xpath)

    def cleanup(self):
        for f in self.rendered_files:
            pattern = str(f).split('/')[-1].replace('.png', '.*')
            for _ in self.cwd.glob(pattern):
                _.unlink()
