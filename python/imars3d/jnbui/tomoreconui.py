# coding: utf-8
from __future__ import print_function

from . import ct_wizard as base
from .ct_wizard import Context, config
import os
import ipywidgets as ipyw
from IPython.display import display
from _utils import js_alert
from ipywe import imageslider as ImgSlider, fileselector as flselect
import pickle as pkl

img_width = 0
img_height = 0
remove_rings = False
smooth_recon = False
smooth_projection = False
start_directory = None


def wizard(context, start_dir=os.path.expanduser("~"), image_width=300, image_height=300, remove_rings_at_sinograms=False, smooth_rec=False, smooth_proj=False):
    """
    Saves several parameters needed for later in the wizard and starts the wizard.

    Parameters
    ----------
    context: Context Object
        Object (from ct_wizard.py) that stores the config
        and ct objects used in the reconstruction process
    start_dir: str
        Starting directory path. Only used if using a previous configuration.
        Initial Value: Home Directory (/~)
    image_width: int
        Width of the images displayed by the widget in pixels.
        Initial Value: 300
    image_height: int
        Height of the images displayed by the widget in pixels.
        Initial Value: 300
    remove_rings_at_sinograms: bool
        If true, the algorithm for removing rings
        at sinograms will be run during reconstruction.
        Initial Value: False
    smooth_rec: bool
        If true, the algorithm for smoothing the reconstruction result
        will be run after reconstruction.
        Initial Value: False
    smooth_proj: bool
        If true, the algorithm for adding extra smoothing
        of the projection will be run after reconstruction.
        Initial Value: False
    """
    global img_width, img_height, remove_rings, smooth_recon, smooth_projection, start_directory
    img_width = image_width
    img_height = image_height
    remove_rings = remove_rings_at_sinograms
    smooth_recon = smooth_rec
    smooth_projection = smooth_proj
    start_directory = start_dir
    WizardPanel(StartButtonPanel(context))
    return


class WizardPanel:
    """Base class for starting the wizard."""
    label_layout = ipyw.Layout(height='35px', padding='8px', width='300px')

    def __init__(self, start_panel):
        display(ipyw.Label("Tomography reconstruction wizard", layout=self.label_layout))
        start_panel.show()
        return


class StartButtonPanel(base.Panel):
    """Creates an explanation of the panel and two buttons
       for either starting the process from scratch or 
       starting with a pre-existing configuration."""
    label_layout = ipyw.Layout(height="32px", padding="2px", width="500px")

    def __init__(self, context):
        """
        Create StartButtonPanel instance.
        
        Parameters
        ----------
        context: Context Object
            Object (from ct_wizard.py) that stores the config
            and ct objects used in the reconstruction process   
        """
        self.context = context
        explanation = ipyw.Label("Do you wish to start from scratch or use a previous reconstruction configuration?", layout=self.label_layout)
        scratch_button = ipyw.Button(description="Start from Scratch",
                                     layout=self.button_layout)
        prev_button = ipyw.Button(description="Previous Config",
                                  layout=self.button_layout)
        buttons = ipyw.HBox(children=[scratch_button, prev_button])
        self.widgets = [explanation, buttons]
        self.panel = ipyw.VBox(children=self.widgets, layout=self.layout)
        scratch_button.on_click(self.nextStep)
        prev_button.on_click(self.reloadConfig)

    def reloadConfig(self, event):
        """Removes the current panel and creates and displays the FileSelectPanel."""
        self.remove()
        fselpan = FileSelectPanel(self.context)
        fselpan.show()

    def nextStep(self, event):
        """Removes the current panel and creates and displays the InstrumentPanel."""
        self.remove()
        inst_panel = InstrumentPanel(self.context)
        inst_panel.show()


class FileSelectPanel(base.Panel):
    """
    Creates a FileSelector widget interface to allow
    the user to select the .pkl file they want to use
    for the reconstruction configuration.
    """

    def __init__(self, context):
        """
        Create FileSelectPanel instance.
        
        Parameters
        ----------
        context: Context Object
            Object (from ct_wizard.py) that stores the config
            and ct objects used in the reconstruction process   
        """
        global start_directory
        self.context = context
        self.fsp = flselect.FileSelectorPanel("Choose a .pkl file to use for configuration",
                                              start_dir=start_directory)

        def createConfig(path):
            """
            Opens the .pkl file chosen and uses it to update self.context.config.
            
            Parameters
            ----------
            path: str
                The path to the selected file
            """
            open_path = open(path)
            self.context.config = pkl.load(open_path)
            if not os.path.exists(self.context.config.outdir):
                os.makedirs(self.context.config.outdir)
            os.chdir(self.context.config.outdir)
            assert os.getcwd() == self.context.config.outdir
            open_config = open('recon-config.pkl', 'wb')
            pkl.dump(self.context.config, open_config)
            for k, v in self.context.config.__dict__.items():
                if k.startswith('_'):
                    continue
                sv = str(v)
                if len(sv) > 60:
                    sv = sv[:50] + '...'
                print("{0:20}{1:<}".format(k, sv))
            open_path.close()
            open_config.close()
            self.nextStep()
        self.fsp.next = createConfig
        self.panel = self.fsp.panel
        self.widgets = self.fsp.widgets

    def nextStep(self):
        """
        Removes the current panel. Then, creates a ct object,
        and saves it into context's ct member.
        Fianlly, creates an ImgSliderPanel and displays it.
        """
        self.remove()
        from imars3d.CT import CT
        context = self.context
        ct = CT(context.config.datadir, CT_subdir=context.config.ct_dir,
                CT_identifier=context.config.ct_sig, workdir=context.config.workdir,
                outdir=context.config.outdir, ob_files=context.config.ob_files,
                df_files=context.config.df_files)
        context.ct = ct
        img_slide = ImgSliderPanel(context)
        img_slide.show()


class InstrumentPanel(base.InstrumentPanel):
    """
    A copy of ct_wizard's InstrumentPanel where
    the validate function is updated to continue
    to this wizard's IPTSpanel class.
    """

    def validate(self, s):
        instrument = self.text.value.encode()
        if instrument.lower() not in self.instruments.keys():
            s = "instrument {} not supported!".format(instrument)
            js_alert(s)
        else:
            self.context.config.instrument = instrument.upper()
            self.context.config.facility = self.instruments[instrument.lower()].upper()
            self.remove()
            ipts_panel = IPTSpanel(self.context)
            ipts_panel.show()
        return


class IPTSpanel(base.IPTSpanel):
    """
    A copy of ct_wizard's IPTSpanel where
    the validate_IPTS function is updated to continue
    to this wizard's ScanNamePanel class.
    """

    def validate_IPTS(self, s):
        ipts1 = self.text.value.encode()
        facility = self.context.config.facility
        instrument = self.context.config.instrument
        path = os.path.abspath('/{0}/{1}/IPTS-{2}'.format(facility, instrument, ipts1))
        if not os.path.exists(path):
            s = "Cannot open directory {} ! Please check IPTS number".format(path)
            js_alert(s)
        else:
            self.context.config.ipts = ipts = ipts1
            # use your experiment IPTS number
            self.context.config.iptsdir = iptsdir = path
            # path to the directory with ct, ob, and df data files or subdirs
            datadir = self.context.config.datadir = os.path.join(iptsdir, "raw/")
            self.remove()
            # make sure there is ct scan directory
            self.context.config.ct_scan_root = ct_scan_root = os.path.join(datadir, 'ct_scans')
            ct_scan_subdirs = [d for d in os.listdir(ct_scan_root) if os.path.isdir(os.path.join(ct_scan_root, d))]
            self.context.config.ct_scan_subdirs = ct_scan_subdirs
            scan_panel = ScanNamePanel(self.context)
            scan_panel.show()
        return


class ScanNamePanel(base.ScanNamePanel):
    """
    A copy of ct_wizard's ScanNamePanel where
    the validate function is updated to continue
    to this wizard's WorkDirPanel class.
    """

    def validate(self, s):
        v = self.text.value
        if not v:
            s = 'Please specify a name for your tomography scan'
            js_alert(s)
        else:
            self.context.config.scan = v.encode()
            self.remove()
            wd_panel = WorkDirPanel(self.context, self.context.config.scan)
            wd_panel.show()
        return


class WorkDirPanel(base.WorkDirPanel):
    """
    A copy of ct_wizard's WorkDirPanel where
    the nextStep function is updated to continue
    to this wizard's OutputDirPanel class.
    """

    def nextStep(self):
        self.context.config.workdir = self.selected
        output_panel = OutputDirPanel(self.context, self.context.config.scan)
        output_panel.show()


class OutputDirPanel(base.OutputDirPanel):
    """
    A copy of ct_wizard's OutputDirPanel where
    the nextStep function is updated to continue
    to this wizard's CTDirPanel class.
    """

    def nextStep(self):
        self.context.config.outdir = self.selected
        ctdir_panel = CTDirPanel(self.context)
        ctdir_panel.show()
    pass


class CTDirPanel(base.CTDirPanel):
    """
    A copy of ct_wizard's CTDirPanel where
    the nextStep function is updated to continue
    to this wizard's CTSigPanel class.
    """

    def nextStep(self):
        next = CTSigPanel(self.context)
        next.show()
        return


class CTSigPanel(base.CTSigPanel):
    """
    A copy of ct_wizard's CTSigPanel where
    the nextStep function is updated to continue
    to this wizard's OBPanel class.
    """

    def nextStep(self):
        next = OBPanel(self.context)
        next.show()
        return


class OBPanel(base.OBPanel):
    """
    A copy of ct_wizard's OBPanel where
    the nextStep function is updated to continue
    to this wizard's DFPanel class.
    """

    def nextStep(self):
        next = DFPanel(self.context)
        next.show()
        return


class DFPanel(base.DFPanel):
    """
    A copy of ct_wizard's DFPanel where the nextStep function
    is updated for the needs of this wizard.
    """

    def nextStep(self):
        """
        Creates and moves to the desired output directory.
        Then, creates/opens that directory's recon-config.pkl file,
        and dumps the contents of self.context.config into it.
        Then, after printing the configuration, creates a ct object,
        and stores the result in context.ct. 
        Finally, removes the current panel,
        and replaces it with an ImgSliderPanel.
        """
        os.makedirs(self.context.config.outdir)
        os.chdir(self.context.config.outdir)
        assert os.getcwd() == self.context.config.outdir
        open_config = open('recon-config.pkl', 'wb')
        pkl.dump(self.context.config, open_config)
        for k, v in self.context.config.__dict__.items():
            if k.startswith('_'):
                continue
            sv = str(v)
            if len(sv) > 60:
                sv = sv[:50] + '...'
            print("{0:20}{1:<}".format(k, sv))
        open_config.close()
        self.remove()
        from imars3d.CT import CT
        context = self.context
        ct = CT(context.config.datadir, CT_subdir=context.config.ct_dir,
                CT_identifier=context.config.ct_sig, workdir=context.config.workdir,
                outdir=context.config.outdir, ob_files=context.config.ob_files,
                df_files=context.config.df_files)
        context.ct = ct
        imgslide = ImgSliderPanel(context)
        imgslide.show()


class ImgSliderPanel(base.Panel):
    """Creates a tab interface where each tab displays
       an ImageSlider widget with either the CT, DF, or OB
       images displayed. In each tab, there is also
       a Reconstruction button to begin the reconstruction process.
       After the reconstruction process is complete,
       a new tab is added that displays
       an ImageSlider of the reconstructed images."""

    def __init__(self, context):
        """
        Create ImgSliderPanel instance.
        
        Parameters
        ----------
        context: Context Object
            Object (from ct_wizard.py) that stores the config
            and ct objects used in the reconstruction process   
        """
        global img_width, img_height
        self.width = img_width
        self.height = img_height
        self.context = context
        ct = context.ct
        self.ppd = ct.preprocess()
        self.df_imgs = ct.dfs
        self.ob_imgs = ct.obs
        self.img_disp = None
        self.ct_slider = ImgSlider.ImageSlider(self.ppd, self.width, self.height)
        self.df_slider = ImgSlider.ImageSlider(self.df_imgs, self.width, self.height)
        self.ob_slider = ImgSlider.ImageSlider(self.ob_imgs, self.width, self.height)
        explanation = ipyw.Label("Select a Region of Interest for the CT, DF, or OB Images", layout=self.label_layout)
        ct_button = ipyw.Button(description="Reconstruct",
                                layout=self.button_layout)
        df_button = ipyw.Button(description="Reconstruct",
                                layout=self.button_layout)
        ob_button = ipyw.Button(description="Reconstruct",
                                layout=self.button_layout)
        ct_tab = ipyw.VBox(children=[self.ct_slider, ct_button],
                           layout=self.layout)
        df_tab = ipyw.VBox(children=[self.df_slider, df_button],
                           layout=self.layout)
        ob_tab = ipyw.VBox(children=[self.ob_slider, ob_button],
                           layout=self.layout)
        self.widgets = [ct_tab, df_tab, ob_tab]
        self.panel = ipyw.Tab(children=self.widgets)
        self.panel.set_title(0, "CT")
        self.panel.set_title(1, "DF")
        self.panel.set_title(2, "OB")
        ct_button.on_click(self.ct_select)
        df_button.on_click(self.df_select)
        ob_button.on_click(self.ob_select)

    def ct_select(self, event):
        """Sets img_disp to ct_slider so the ROI values can be obtained"""
        self.img_disp = self.ct_slider
        self.nextStep()

    def df_select(self, event):
        """Sets img_disp to df_slider so the ROI values can be obtained"""
        self.img_disp = self.df_slider
        self.nextStep()

    def ob_select(self, event):
        """Sets img_disp to ob_slider so the ROI values can be obtained"""
        self.img_disp = self.ob_slider
        self.nextStep()

    def nextStep(self):
        """
        Grabs the ROI values from img_disp.
        Then, uses those values and the globals set
        in the starting function to begin the reconstruction process.
        Once the process is complete, prints the working directory
        for the process. Finally, creates an ImageSlider widget
        using the reconstructed images, and appends it
        as a fourth tab in the currently displayed panel.
        """
        xmin = self.img_disp._xcoord_absolute
        ymin = self.img_disp._ycoord_absolute
        xmax = self.img_disp._xcoord_max_roi
        ymax = self.img_disp._ycoord_max_roi
        global remove_rings, smooth_recon, smooth_projection
        self.context.ct.recon(crop_window=(xmin, ymin, xmax, ymax),
                              remove_rings_at_sinograms=remove_rings,
                              smooth_recon=smooth_recon,
                              smooth_projection=smooth_projection)
        print(self.context.config.workdir)
        recon_slider = ImgSlider.ImageSlider(self.context.ct.r.reconstructed,
                                             self.width, self.height)
        recon_tab = ipyw.VBox(children=[recon_slider], layout=self.layout)
        self.widgets.append(recon_tab)
        self.panel.children = list(self.panel.children) + [recon_tab]
        self.panel.set_title(3, "Output")