"""
checks all result files(all xxxxx_processed.prickle) an writes results to /result/
"""
import csv
import glob
import json
import pickle
import statistics
from itertools import groupby

import os


def weights_to_string(weights):
    """
    converts an array of ints to string
    :param weights:
    :return:
    """
    scaled_weights_string = [str(x) for x in weights]
    return '_'.join(scaled_weights_string)


def process_files(path, praefix):
    """
    reads all processed q items an merges them into one dict
    :param path:
    :return:
    """
    score_results = {}

    # walk over app items directories
    for directory_path in glob.glob(path):
        if praefix is None or (praefix and directory_path.find(praefix) != -1):
            # walk over all parts
            entire_qu = []
            for file_path in glob.glob(directory_path + '/*'):
                if os.path.getsize(file_path) > 0:
                    with open(file_path, 'rb') as ff:
                        processed_item = pickle.load(ff)
                        entire_qu.append(processed_item)

            # merge qu to one dict, merge per question and weight
            for result in entire_qu:
                # walk over each result object,
                # each extractor can answer more than one question
                for question in result['result']:
                    question_scores = score_results.setdefault(question, {})
                    weights = result['result'][question][1]

                    # create a identifier for these weights
                    weights_string = weights_to_string(weights)

                    # each item is identified by their extracting parameters, weight
                    # and their answer (stored over the parent node)
                    comb_for_this_parameter_id = question_scores.setdefault(result['extracting_parameters_id'], { 'extracting_parameters': result['extracting_parameters'], 'weights': {}})

                    comb = comb_for_this_parameter_id['weights'].setdefault(weights_string, {'weights': weights, 'scores_doc': []})

                    # save this score to all results
                    comb['scores_doc'].append(result['result'][question][2])

    evaluate(score_results, write_full=False, praefix=praefix)


def remove_errors(list):
    """
    returns a list where all -1 are replace with the biggest value and all oder negative entries are removed at all
    :param list:
    :return:
    """
    # remove no annotation error, by replacing with worst distance
    a_max = max(list)
    tmp = [a_max if v is -1 else v for v in list]

    # remove other errors
    result = [x for x in tmp if x and x >= 0]
    return result


def normalize(list):
    """
    this is assuming that there is a min with 0
    :param list:
    :return:
    """
    # find max
    a_max = max(list)
    # set errors to max
    list_error_free = [x if x >= 0 else a_max for x in list]
    # normalize
    result = []
    for entry in list_error_free:
        result.append(entry / a_max)

    return result


def merge_top(a_list, accessor):
    """
    multiple weights can produce the same top-score, this function merges all top weights.
    :param a_list: 
    :param accessor: 
    :return: 
    """
    a_list.sort(key=lambda x: x['score'], reverse=False)
    result = a_list[0]
    weights = []
    result['weights'] = weights

    for entry in a_list:
        if entry[accessor] == result[accessor]:
            a_weight = entry.get('weight')
            if a_weight:
                weights.append(a_weight)
        else:
            break
    return result


def to_ranges(iterable):
    """
    finds range of ints in a list of ints, this returns a generator!!
    :param iterable:
    :return:
    """
    iterable = sorted(set(iterable))
    for key, group in groupby(enumerate(iterable), lambda t: t[1] - t[0]):
        group = list(group)
        yield group[0][1], group[-1][1]


def to_ranges_wrapper(iterable, decimals: int = 10):
    """
    converts a list of float to ints and finds range in this list
    :param iterable:
    :return:
    """

    for ita, i in enumerate(iterable):
        iterable[ita] = int(iterable[ita] * decimals)

    result = list(to_ranges(iterable))

    return result


def stats_helper(list):
    """
    https://docs.python.org/3/library/statistics.html#statistics.pvariance
    :param list:
    :return:
    """
    mean = statistics.mean(list)

    mode = None
    try:
        mode = statistics.mode(list)
    except statistics.StatisticsError:
        # no unique mode
        pass

    return {
        'mean':   mean,
        'variance': statistics.pvariance(list, mu=mean),
        'standard_deviation': statistics.pstdev(list, mu=mean),
        'harmonic_mean': statistics.harmonic_mean(list),
        'median':statistics.median(list),
        'median_low':statistics.median_low(list),
        'median_high':statistics.median_high(list),
        'median_grouped':statistics.median_grouped(list),
        'mode': mode
    }


def golden_weights_to_ranges(a_list):
    """
    converts golden weights to ranges per weight to make importance more visible
    [0.1, 0.1] [0.2, 0.1] [0.3, 0.9]

    this function works only well with 0.1 step weights, result is not  converted back to float
    ---->
    {
        0: [1 - 3]
        1: [1 - 1] [0.9 - 0.9]
    }
    "EXPERIMENTAL - NOT VERY WELL TESTED"

    :param a_list: 
    :return: 
    """
    golden_weights = a_list.get('best_dist')['weights']
    if golden_weights and len(golden_weights) > 0:
        # slots for each weight

        weights = [[] for _ in range(len(golden_weights[0]))]

        # copy weights based on their location into new format
        for combination in golden_weights:
            for i, weight in enumerate(combination):
                weights[i].append(weight)

        # find the ranges per weight location
        results = []
        for weight in weights:
            uniqu_weights = list(set(weight))
            uniqu_weights.sort()

            ranges = to_ranges_wrapper(uniqu_weights)
            results.append({
                'stats': stats_helper(weight),
                'data': ranges
            })



        a_list['golden_groups'] = results


def index_of_best(list):
    """
    low distance is better
    :param list:
    :return:
    """
    a_list = remove_errors(list)
    return list.index(min(a_list))


def evaluate(score_results, write_full: bool=False, praefix=''):

    # write raw results
    if write_full:
        with open('result/' + praefix + '_evaluation_full' + '.json', 'w') as data_file:
            data_file.write(json.dumps(score_results, sort_keys=False, indent=4))
            data_file.close()


    # has a low dist on average per weight (documents are merged)
    score_per_average = {}
    # results_error_rate = {}
    for question in score_results:
        for extracting_parameters_id in score_results[question]:
            extracting_parameters = score_results[question][extracting_parameters_id]
            for combination_string in score_results[question][extracting_parameters_id]['weights']:
                combo = score_results[question][extracting_parameters_id]['weights'][combination_string]

                raw_scores = combo['scores_doc']
                scores_norm = normalize(raw_scores)
                a_sum = sum(scores_norm)

                combo['norm_avg'] = a_sum / len(scores_norm)
                score_per_average.setdefault(question + '_' + str(extracting_parameters_id), {})[combination_string] = {
                    'score': a_sum,
                    'norm_avg': combo['norm_avg'],
                    'weight': combo['weights']
                   #, 'extracting_parameter': extracting_parameters
                }
    # nice formatted full output, if anyone needs is
    if write_full:
        nice_format = {}
        for question in score_results:
            question_scores = nice_format.setdefault(question, [])
            for combination_string in score_results[question]:
                combo = score_results[question][combination_string]
                del combo['scores_doc']
                question_scores.append(combo)

        with open('result/' + praefix + '_evaluation_only_avg' + '.json', 'w') as data_file:
            data_file.write(json.dumps(nice_format, sort_keys=False, indent=4))
            data_file.close()

    # finally, get the best weighting and save it to a file
    final_result = {}
    for question in score_per_average:
        score_per_average_list = list(score_per_average[question].values())

        score_per_average_list.sort(key=lambda x: x['norm_avg'], reverse=False)

        final_result[question] = {
            'best_dist': merge_top(score_per_average_list, 'norm_avg')
        }

        golden_weights_to_ranges(final_result[question])


    csv_line = [
          'extractor',
          'question',
          'weight',
          'range',
          'mean',
          'std'
    ]
    # write it as json
    for question in final_result:
        with open('result/' + praefix + '_final_result_' + question + '.json', 'w') as data_file:
            data_file.write(json.dumps(final_result[question], sort_keys=False, indent=4))
            data_file.close()

    # write it as CSV
    for question in final_result:
        pass

   # with open(os.path.dirname(__file__) + '/final_result.csv','w') as csv_file:
    #    writer = csv.writer(csv_file)
     #   for line in outputs:
      #      writer.writerow(line)

if __name__ == '__main__':
    process_files('queue_caches/*_processed*/', praefix='training')
    process_files('queue_caches/*_processed*/', praefix='test')


