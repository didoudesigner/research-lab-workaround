from modPredictor import *
from modPaper import *

from predictor import *
from paper import *

import numpy as np



class PubMexInference:
    '''
    PubMex model wrapper
    '''

    def __init__(self, model_dump="../models/model_final.pth", config_file="../configs/train_config.yaml", pretrained=True, use_cuda=True, confidence_threshold=0.7):
        '''
        :param model_dir: path to the model dump (.pkl-file)
        :param config_path: path to the config file (.yaml-file)
        :param use_cuda: whether to run on a GPU (effective only when there is a GPU)
        :param parallel: when to use DataParallel to infer on multiple GPUs (effective only when `use_cuda=True`and there are multiple available GPUs)
        :param confidence_threshold: minimum score for instance predictions to be shown
        '''

        self.metadataCatalog = MetadataCatalog.get("dla_val")
        self.metadataCatalog.thing_classes = [
            "abstract", "address", "affiliation", "author", "date", "doi", "email", "journal", "title"
            ]

        self.cfg = get_cfg()
        self.cfg.merge_from_file(config_file)
        self.cfg.MODEL.WEIGHTS = model_dump
        self.cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = confidence_threshold
        self.cfg.MODEL.DEVICE = 'cuda' if use_cuda else 'cpu'

        self.predictor = Predictor(self.cfg)
        self.mod_predictor = ModPredictor(self.cfg)

    def predict(self, pdf_file, page=0, margin=1, use_fitz=False):
        '''
        :param pdf_file: path to the PDF file to run the inference on
        :param page: the page number 
        :param margin: margin to be added to the predicted bounding boxes when extracting the text from the PDF
        :param use_fitz: whether to use the `fitz` library to retrieve the text from the PDF. If set to False, the model uses 
        '''
        paper = Paper(pdf_file, {}, metadata_page=page)
        paper.resize_image() 

        img = np.asarray(paper.image)[:, :, ::-1].copy()

        v = Visualizer(
            img[:, : , ::-1],
            metadata=self.metadataCatalog,
            scale=1,
            instance_mode=ColorMode.IMAGE_BW # remove the colors of unsegmented pixels
            )
        outputs = self.predictor(img)
        v = v.draw_instance_predictions(outputs["instances"].to("cpu"))

        # get the text corresponding to the tensors predicted by the model from the PDF
        paper.get_text_from_detectron2_outputs(
            outputs["instances"], 
            self.metadataCatalog, 
            margin=margin,
            use_fitz=use_fitz)

        paper.post_process_metadata()

        return v, paper.metadata

    def alt_predict(self, pdf_file, page=0, margin=1, use_fitz=False):
        """
        Same parameter as predict
        output : list of list, each list contain text, coordinate and score for each class
                eg. [ [text, score, coordinate],[] ]

                    text        ('Geständnismotivierung inBeschuldigtenvernehmungen: zur hermeneutischenund diskursanalytischen Rekonstruktion vonWissen', 
                    coordinate  (tensor([ 55.2479, 188.3373, 501.5481, 282.2487]),
                    score       tensor([2.0727e-04, 1.5972e-04, 2.3315e-04, 6.9249e-04, 1.9704e-04, 8.5286e-05,8.2874e-05, 5.5666e-04, 9.9734e-01, 4.4707e-04])))
        """

        paper = ModPaper(pdf_file, {}, metadata_page=page)
        paper.resize_image() 

        img = np.asarray(paper.image)[:, :, ::-1].copy()
        
        predict = self.mod_predictor(img)
        
        text = []
        for i, value in enumerate(predict):
            text.append(paper.get_text_from_bbox(predict[i][0][0], predict[i][0][1], predict[i][0][2], predict[i][0][3]))
        result = list(zip(text, [score for _, score in predict]))  

        return result
    

    def visualize_output(self, visualizer_instance):
        '''
        :param visualizer_instance: the visualizer instance generated by PubMexInference's predict() method
        '''
        cv2.imshow("image",visualizer_instance.get_image()[:, :, ::-1])
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
