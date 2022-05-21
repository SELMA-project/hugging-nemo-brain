import os

from beartype import beartype

from huggingface_wav2vec2_finetuning.base_model_for_finetuning import (
    BaseModelForFinetuning,
    ModelIdentity,
)
from huggingface_wav2vec2_finetuning.huggingface_wav2vec2_finetuner import (
    TrainArgs,
    HFWav2vec2Finetuner,
)
from huggingface_wav2vec2_finetuning.stream_ftdataset import IterableASRCorporaDataset
from misc_utils.prefix_suffix import BASE_PATHES, PrefixSuffix
from ml4audio.audio_data.mls_corpora import MLSIterableDataset, MLSTarGzTranscripts
from ml4audio.audio_data.targz_asr_dataset import TarGzArrayText
from ml4audio.audio_utils.audio_data_models import AudioTextData


@beartype
def create_finetuner(
    run_name_for_wandb: str,
    model_to_finetune: ModelIdentity,
    train_corpus: AudioTextData,
    eval_corpus: AudioTextData,
    do_normalize_audio: bool,
):
    augmentations = [
        # TranscodePerturbationDC(0.5),
        # SoxPerturbations(proba=0.75),
    ]
    fm = BaseModelForFinetuning(
        model_to_finetune=model_to_finetune,
        text_normalizer="de",
        new_vocab=None,
        do_normalize_audio=do_normalize_audio,
    )
    finetune_task = HFWav2vec2Finetuner(
        finetune_model=fm,
        train_dataset=IterableASRCorporaDataset(
            corpus=train_corpus,
            finetune_model=fm,
            perturbations=augmentations,
            limit=100_000,
        ),
        eval_dataset=IterableASRCorporaDataset(
            corpus=eval_corpus, finetune_model=fm, limit=100
        ),
        train_args=TrainArgs(
            run_name=run_name_for_wandb,
            overwrite_output_dir=True,
            max_steps=10_000,
            num_train_epochs=1,
            # per_device_train_batch_size=6,
            per_device_train_batch_size=6,
            per_device_eval_batch_size=1,
            learning_rate=1.0e-05,
            warmup_steps=500,
            evaluation_strategy="steps",
            save_steps=20_000,
            eval_steps=20_000,
            # save_steps=10,
            # eval_steps=10,
            # logging_steps=5,
            logging_steps=100,
            save_total_limit=3,
            dataloader_num_workers=4,
            no_cuda=False,
            fp16=True,
            group_by_length=False,
            ignore_data_skip=True,
        ),
        overwrite_old_cache=True,
    )
    return finetune_task


if __name__ == "__main__":

    base_path = os.environ["BASE_PATH"]
    data_root = os.environ["DATA_ROOT"]
    cache_root = f"{base_path}/data/cache"
    BASE_PATHES["data_root"] = data_root
    BASE_PATHES["cache_root"] = cache_root
    BASE_PATHES["base_path"] = base_path
    BASE_PATHES["finetune_training"] = PrefixSuffix("cache_root", f"FINETUNE_TRAINING")
    BASE_PATHES["raw_data"] = PrefixSuffix(
        "cache_root", f"RAW_DATA"
    )  # TODO: I'm confused! when str ? when PrefixSuffix?
    BASE_PATHES["finetune_results"] = PrefixSuffix("cache_root", f"FINETUNE_RESULTS")

    experiments = (
        finetune_task
        for model_to_finetune in [
            ModelIdentity("jonatasgrosman/wav2vec2-large-xlsr-53-german"),
        ]
        for eval_corpus in [
            TarGzArrayText(
                corpus=MLSIterableDataset(
                    targztranscripts=MLSTarGzTranscripts(
                        targz_file=str(PrefixSuffix("data_root", "mls_german.tar.gz"))
                    ),
                    split="test",
                ),
                sample_rate=16000,
            )
        ]
        for train_corpus in [
            TarGzArrayText(
                corpus=MLSIterableDataset(
                    targztranscripts=MLSTarGzTranscripts(
                        targz_file=str(PrefixSuffix("data_root", "mls_german.tar.gz"))
                    ),
                    split="train",
                ),
                sample_rate=16000,
            )
        ]
        for norm_audio in [True]
        for run_name in [f"debug_run_directly"]
        for finetune_task in [
            create_finetuner(
                run_name_for_wandb=run_name,
                model_to_finetune=model_to_finetune,
                train_corpus=train_corpus,
                eval_corpus=eval_corpus,
                do_normalize_audio=norm_audio,
            )
        ]
    )
    for exp in experiments:
        exp.build()
    # first_finetuned = FinetunedModel(finetune_master=o)
